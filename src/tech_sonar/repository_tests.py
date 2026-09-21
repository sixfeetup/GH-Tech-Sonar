import dataclasses
import json
import pathlib
import subprocess

import pytest

from tech_sonar import model
from tech_sonar import repository


@dataclasses.dataclass
class FakeRunner:
    outputs: dict[tuple[str, ...], str]
    calls: list[tuple[tuple[str, ...], pathlib.Path | None]] = (
        dataclasses.field(default_factory=list)
    )

    def __call__(
        self,
        arguments: tuple[str, ...],
        cwd: pathlib.Path | None,
    ) -> str:
        self.calls.append((arguments, cwd))
        return self.outputs.get(arguments, "")


def test_run_command_executes_and_returns_stdout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    def run(
        arguments: tuple[str, ...],
        **options: object,
    ) -> subprocess.CompletedProcess[str]:
        assert arguments == ("git", "rev-parse", "HEAD")
        assert options == {
            "cwd": tmp_path,
            "check": True,
            "capture_output": True,
            "text": True,
        }
        return subprocess.CompletedProcess(arguments, 0, "abc123\n", "")

    monkeypatch.setattr(subprocess, "run", run)

    assert repository.run_command(
        ("git", "rev-parse", "HEAD"),
        tmp_path,
    ) == "abc123"


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (OSError("permission denied"), "permission denied"),
        (
            subprocess.CalledProcessError(
                1,
                ("git", "status", "--porcelain"),
                stderr="fatal: not a repository\n",
            ),
            "fatal: not a repository",
        ),
    ],
)
def test_run_command_translates_execution_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: OSError | subprocess.CalledProcessError,
    message: str,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(subprocess, "run", fail)

    with pytest.raises(repository.RepositoryError) as raised:
        repository.run_command(("git", "status", "--porcelain"))

    assert "git status --porcelain" in str(raised.value)
    assert message in str(raised.value)


def test_inspect_discovers_repository_state(tmp_path: pathlib.Path) -> None:
    runner = FakeRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): f"{tmp_path}\n",
            ("git", "status", "--porcelain"): "",
            ("git", "branch", "--show-current"): "main\n",
            (
                "gh",
                "repo",
                "view",
                "--json",
                "nameWithOwner,defaultBranchRef",
            ): json.dumps(
                {
                    "nameWithOwner": "sixfeetup/example",
                    "defaultBranchRef": {"name": "main"},
                },
            ),
        },
    )

    state = repository.inspect(tmp_path, runner)

    assert state == repository.State(
        root=tmp_path,
        repository=model.Repository("sixfeetup", "example"),
        default_branch="main",
        current_branch="main",
    )
    assert runner.calls == [
        (("git", "rev-parse", "--show-toplevel"), tmp_path),
        (("git", "status", "--porcelain"), tmp_path),
        (("git", "branch", "--show-current"), tmp_path),
        (
            (
                "gh",
                "repo",
                "view",
                "--json",
                "nameWithOwner,defaultBranchRef",
            ),
            tmp_path,
        ),
    ]


def test_inspect_rejects_detached_head(tmp_path: pathlib.Path) -> None:
    runner = FakeRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): f"{tmp_path}\n",
            ("git", "status", "--porcelain"): "",
            ("git", "branch", "--show-current"): "",
        },
    )

    with pytest.raises(repository.RepositoryError, match="detached HEAD"):
        repository.inspect(tmp_path, runner)

    assert runner.calls == [
        (("git", "rev-parse", "--show-toplevel"), tmp_path),
        (("git", "status", "--porcelain"), tmp_path),
        (("git", "branch", "--show-current"), tmp_path),
    ]


def test_repository_at_discovers_name_with_owner(tmp_path: pathlib.Path) -> None:
    command = (
        "gh",
        "repo",
        "view",
        "--json",
        "nameWithOwner",
        "--jq",
        ".nameWithOwner",
    )
    runner = FakeRunner({command: "sixfeetup/example\n"})

    assert repository.repository_at(tmp_path, runner) == model.Repository(
        "sixfeetup",
        "example",
    )
    assert runner.calls == [(command, tmp_path)]


def test_require_clean_rejects_porcelain_output(tmp_path: pathlib.Path) -> None:
    runner = FakeRunner(
        {("git", "status", "--porcelain"): " M README.md\n"},
    )

    with pytest.raises(repository.RepositoryError, match="not clean"):
        repository.require_clean(tmp_path, runner)


def test_source_revision_requires_clean_checkout(tmp_path: pathlib.Path) -> None:
    runner = FakeRunner(
        {
            ("git", "status", "--porcelain"): "",
            ("git", "rev-parse", "HEAD"): "abc123\n",
        },
    )

    assert repository.source_revision(tmp_path, runner) == "abc123"
    assert runner.calls == [
        (("git", "status", "--porcelain"), tmp_path),
        (("git", "rev-parse", "HEAD"), tmp_path),
    ]


@pytest.mark.parametrize(
    "response",
    [
        "not JSON",
        json.dumps(
            {
                "nameWithOwner": 42,
                "defaultBranchRef": {"name": "main"},
            },
        ),
    ],
)
def test_inspect_reports_malformed_github_json(
    tmp_path: pathlib.Path,
    response: str,
) -> None:
    runner = FakeRunner(
        {
            ("git", "rev-parse", "--show-toplevel"): f"{tmp_path}\n",
            ("git", "status", "--porcelain"): "",
            ("git", "branch", "--show-current"): "main\n",
            (
                "gh",
                "repo",
                "view",
                "--json",
                "nameWithOwner,defaultBranchRef",
            ): response,
        },
    )

    with pytest.raises(repository.RepositoryError, match="malformed"):
        repository.inspect(tmp_path, runner)


def test_clone_uses_repository_and_destination(tmp_path: pathlib.Path) -> None:
    destination = tmp_path / "example"
    command = (
        "gh",
        "repo",
        "clone",
        "sixfeetup/example",
        str(destination),
    )
    runner = FakeRunner({command: ""})

    result = repository.clone(
        model.Repository("sixfeetup", "example"),
        destination,
        runner,
    )

    assert result == destination
    assert runner.calls == [(command, None)]


def test_label_names_returns_raw_names(tmp_path: pathlib.Path) -> None:
    command = (
        "gh",
        "label",
        "list",
        "--limit",
        "1000",
        "--json",
        "name",
        "--jq",
        ".[].name",
    )
    runner = FakeRunner({command: "SONAR ADOPT\nsonar explore\n"})

    assert repository.label_names(tmp_path, runner) == frozenset(
        {"SONAR ADOPT", "sonar explore"},
    )
    assert runner.calls == [(command, tmp_path)]


def test_inherited_issue_templates_returns_template_files() -> None:
    response = json.dumps(
        {
            "data": {
                "repository": {
                    "object": {
                        "entries": [
                            {
                                "name": "bug.yml",
                                "type": "blob",
                                "object": {"text": "name: Bug\n"},
                            },
                            {
                                "name": "notes",
                                "type": "tree",
                                "object": {},
                            },
                        ],
                    },
                },
            },
        },
    )
    command = (
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={repository._INHERITED_TEMPLATES_QUERY}",
        "-F",
        "owner=sixfeetup",
    )
    runner = FakeRunner({command: response})

    assert repository.inherited_issue_templates("sixfeetup", runner) == {
        pathlib.Path(".github/ISSUE_TEMPLATE/bug.yml"): "name: Bug\n",
    }
    assert runner.calls == [(command, None)]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (None, None),
        ({"object": None}, {}),
    ],
)
def test_inherited_issue_templates_handles_unavailable_sources(
    source: object,
    expected: dict[pathlib.Path, str] | None,
) -> None:
    command = (
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={repository._INHERITED_TEMPLATES_QUERY}",
        "-F",
        "owner=sixfeetup",
    )
    runner = FakeRunner(
        {
            command: json.dumps(
                {"data": {"repository": source}},
            ),
        },
    )

    assert repository.inherited_issue_templates("sixfeetup", runner) == expected


@pytest.mark.parametrize(
    "response",
    [
        "not JSON",
        json.dumps({"data": {}}),
    ],
)
def test_inherited_issue_templates_reports_malformed_github_json(
    response: str,
) -> None:
    command = (
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={repository._INHERITED_TEMPLATES_QUERY}",
        "-F",
        "owner=sixfeetup",
    )
    runner = FakeRunner({command: response})

    with pytest.raises(repository.RepositoryError, match="malformed"):
        repository.inherited_issue_templates("sixfeetup", runner)


def test_create_label_uses_all_label_fields(tmp_path: pathlib.Path) -> None:
    command = (
        "gh",
        "label",
        "create",
        "SONAR ADOPT",
        "--color",
        "0E8A16",
        "--description",
        "Approved for adoption.",
    )
    runner = FakeRunner({command: ""})

    repository.create_label(
        tmp_path,
        name="SONAR ADOPT",
        color="0E8A16",
        description="Approved for adoption.",
        run=runner,
    )

    assert runner.calls == [(command, tmp_path)]


def test_branch_exists_checks_local_and_remote_branches(
    tmp_path: pathlib.Path,
) -> None:
    local = ("git", "branch", "--list", "topic")
    remote = (
        "git",
        "ls-remote",
        "--heads",
        "origin",
        "refs/heads/topic",
    )
    runner = FakeRunner(
        {
            local: "",
            remote: "abc123\trefs/heads/topic\n",
        },
    )

    assert repository.branch_exists(tmp_path, "topic", runner)
    assert runner.calls == [(local, tmp_path), (remote, tmp_path)]


def test_branch_exists_stops_when_local_branch_exists(
    tmp_path: pathlib.Path,
) -> None:
    local = ("git", "branch", "--list", "topic")
    runner = FakeRunner({local: "  topic\n"})

    assert repository.branch_exists(tmp_path, "topic", runner)
    assert runner.calls == [(local, tmp_path)]


def test_create_branch_switches_to_new_branch(tmp_path: pathlib.Path) -> None:
    command = ("git", "switch", "-c", "topic")
    runner = FakeRunner({command: ""})

    repository.create_branch(tmp_path, "topic", runner)

    assert runner.calls == [(command, tmp_path)]


def test_commit_and_push_stages_only_managed_files(
    tmp_path: pathlib.Path,
) -> None:
    managed_paths = (
        pathlib.Path(".github/workflows/tech-sonar.yml"),
        pathlib.Path(".github/ISSUE_TEMPLATE/technology.yml"),
    )
    commands = [
        (
            "git",
            "add",
            "--",
            ".github/workflows/tech-sonar.yml",
            ".github/ISSUE_TEMPLATE/technology.yml",
        ),
        ("git", "commit", "-m", "chore: install Tech Sonar"),
        ("git", "push", "-u", "origin", "HEAD"),
    ]
    runner = FakeRunner({command: "" for command in commands})

    repository.commit_and_push(
        tmp_path,
        "chore: install Tech Sonar",
        managed_paths,
        runner,
    )

    assert runner.calls == [(command, tmp_path) for command in commands]


def test_open_pull_request_reuses_existing_pr(tmp_path: pathlib.Path) -> None:
    command = (
        "gh",
        "pr",
        "list",
        "--head",
        "topic",
        "--base",
        "main",
        "--state",
        "open",
        "--json",
        "url",
        "--jq",
        ".[0].url",
    )
    runner = FakeRunner(
        {command: "https://github.com/sixfeetup/example/pull/10"},
    )

    url = repository.open_pull_request(
        tmp_path,
        branch="topic",
        base="main",
        title="Update Tech Sonar",
        body="Managed by Tech Sonar.",
        run=runner,
    )

    assert url.endswith("/pull/10")
    assert not any(
        call[0][0:3] == ("gh", "pr", "create")
        for call in runner.calls
    )


def test_open_pull_request_creates_pr_when_none_exists(
    tmp_path: pathlib.Path,
) -> None:
    list_command = (
        "gh",
        "pr",
        "list",
        "--head",
        "topic",
        "--base",
        "main",
        "--state",
        "open",
        "--json",
        "url",
        "--jq",
        ".[0].url",
    )
    create_command = (
        "gh",
        "pr",
        "create",
        "--head",
        "topic",
        "--base",
        "main",
        "--title",
        "Update Tech Sonar",
        "--body",
        "Managed by Tech Sonar.",
    )
    runner = FakeRunner(
        {
            list_command: "",
            create_command: "https://github.com/sixfeetup/example/pull/11\n",
        },
    )

    url = repository.open_pull_request(
        tmp_path,
        branch="topic",
        base="main",
        title="Update Tech Sonar",
        body="Managed by Tech Sonar.",
        run=runner,
    )

    assert url == "https://github.com/sixfeetup/example/pull/11"
    assert runner.calls == [
        (list_command, tmp_path),
        (create_command, tmp_path),
    ]
