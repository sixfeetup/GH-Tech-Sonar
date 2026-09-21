import collections.abc
import dataclasses
import json
import pathlib
import subprocess
from typing import Any

from tech_sonar import model


CommandRunner = collections.abc.Callable[
    [tuple[str, ...], pathlib.Path | None],
    str,
]


class RepositoryError(RuntimeError):
    pass


_INHERITED_TEMPLATES_QUERY = """
query($owner: String!) {
  repository(owner: $owner, name: ".github") {
    object(expression: "HEAD:.github/ISSUE_TEMPLATE") {
      ... on Tree {
        entries {
          name
          type
          object { ... on Blob { text } }
        }
      }
    }
  }
}
""".strip()


@dataclasses.dataclass(frozen=True, slots=True)
class State:
    root: pathlib.Path
    repository: model.Repository
    default_branch: str
    current_branch: str


def run_command(
    arguments: tuple[str, ...],
    cwd: pathlib.Path | None = None,
) -> str:
    try:
        result = subprocess.run(
            arguments,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise RepositoryError(
            f"command {' '.join(arguments)} failed: {error}",
        ) from error
    except subprocess.CalledProcessError as error:
        raise RepositoryError(
            f"command {' '.join(arguments)} failed: {error.stderr.strip()}",
        ) from error
    return result.stdout.strip()


def repository_at(
    path: pathlib.Path,
    run: CommandRunner = run_command,
) -> model.Repository:
    value = run(
        (
            "gh",
            "repo",
            "view",
            "--json",
            "nameWithOwner",
            "--jq",
            ".nameWithOwner",
        ),
        path,
    )
    try:
        return model.Repository.parse(value.strip())
    except ValueError as error:
        raise RepositoryError(
            "GitHub returned malformed repository metadata",
        ) from error


def require_clean(
    path: pathlib.Path,
    run: CommandRunner = run_command,
) -> None:
    status = run(("git", "status", "--porcelain"), path)
    if status.strip():
        raise RepositoryError(f"repository worktree is not clean: {path}")


def source_revision(
    path: pathlib.Path,
    run: CommandRunner = run_command,
) -> str:
    require_clean(path, run)
    return run(("git", "rev-parse", "HEAD"), path).strip()


def inspect(
    path: pathlib.Path,
    run: CommandRunner = run_command,
) -> State:
    root = pathlib.Path(
        run(("git", "rev-parse", "--show-toplevel"), path).strip(),
    )
    require_clean(root, run)
    current_branch = run(("git", "branch", "--show-current"), root).strip()
    if not current_branch:
        raise RepositoryError("repository is in detached HEAD state")
    response = run(
        (
            "gh",
            "repo",
            "view",
            "--json",
            "nameWithOwner,defaultBranchRef",
        ),
        root,
    )
    try:
        metadata: dict[str, Any] = json.loads(response)
        name_with_owner = metadata["nameWithOwner"]
        default_branch = metadata["defaultBranchRef"]["name"]
        if not isinstance(name_with_owner, str):
            raise TypeError("repository name is not a string")
        if not isinstance(default_branch, str):
            raise TypeError("default branch is not a string")
        repository = model.Repository.parse(name_with_owner)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise RepositoryError(
            "GitHub returned malformed repository metadata",
        ) from error
    return State(
        root=root,
        repository=repository,
        default_branch=default_branch,
        current_branch=current_branch,
    )


def clone(
    repository: model.Repository,
    destination: pathlib.Path,
    run: CommandRunner = run_command,
) -> pathlib.Path:
    run(
        ("gh", "repo", "clone", str(repository), str(destination)),
        None,
    )
    return destination


def inherited_issue_templates(
    owner: str,
    run: CommandRunner = run_command,
) -> dict[pathlib.Path, str] | None:
    response = run(
        (
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={_INHERITED_TEMPLATES_QUERY}",
            "-F",
            f"owner={owner}",
        ),
        None,
    )
    try:
        data: dict[str, Any] = json.loads(response)
        source = data["data"]["repository"]
        if source is None:
            return None
        tree = source["object"]
        if tree is None:
            return {}
        return {
            pathlib.Path(".github/ISSUE_TEMPLATE") / entry["name"]:
            entry["object"]["text"]
            for entry in tree["entries"]
            if entry["type"] == "blob"
        }
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise RepositoryError(
            "GitHub returned malformed inherited issue-template data",
        ) from error


def label_names(
    path: pathlib.Path,
    run: CommandRunner = run_command,
) -> frozenset[str]:
    output = run(
        (
            "gh",
            "label",
            "list",
            "--limit",
            "1000",
            "--json",
            "name",
            "--jq",
            ".[].name",
        ),
        path,
    )
    return frozenset(output.strip().splitlines())


def create_label(
    path: pathlib.Path,
    *,
    name: str,
    color: str,
    description: str,
    run: CommandRunner = run_command,
) -> None:
    run(
        (
            "gh",
            "label",
            "create",
            name,
            "--color",
            color,
            "--description",
            description,
        ),
        path,
    )


def branch_exists(
    path: pathlib.Path,
    branch: str,
    run: CommandRunner = run_command,
) -> bool:
    local = run(("git", "branch", "--list", branch), path)
    if local.strip():
        return True
    remote = run(
        (
            "git",
            "ls-remote",
            "--heads",
            "origin",
            f"refs/heads/{branch}",
        ),
        path,
    )
    return bool(remote.strip())


def create_branch(
    path: pathlib.Path,
    branch: str,
    run: CommandRunner = run_command,
) -> None:
    run(("git", "switch", "-c", branch), path)


def commit_and_push(
    path: pathlib.Path,
    message: str,
    managed_paths: collections.abc.Iterable[pathlib.Path],
    run: CommandRunner = run_command,
) -> None:
    run(
        ("git", "add", "--", *(str(item) for item in managed_paths)),
        path,
    )
    run(("git", "commit", "-m", message), path)
    run(("git", "push", "-u", "origin", "HEAD"), path)


def open_pull_request(
    path: pathlib.Path,
    *,
    branch: str,
    base: str,
    title: str,
    body: str,
    run: CommandRunner = run_command,
) -> str:
    existing = run(
        (
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--base",
            base,
            "--state",
            "open",
            "--json",
            "url",
            "--jq",
            ".[0].url",
        ),
        path,
    ).strip()
    if existing:
        return existing
    return run(
        (
            "gh",
            "pr",
            "create",
            "--head",
            branch,
            "--base",
            base,
            "--title",
            title,
            "--body",
            body,
        ),
        path,
    ).strip()
