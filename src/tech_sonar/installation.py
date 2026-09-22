import collections.abc
import dataclasses
import datetime
import importlib.resources
import pathlib
import secrets

from tech_sonar import model
from tech_sonar import repository


MANAGED_WORKFLOW = pathlib.Path(".github/workflows/tech-sonar.yml")
MANAGED_ISSUE_TEMPLATE = pathlib.Path(
    ".github/ISSUE_TEMPLATE/technology.yml",
)
_REVISION_MARKER = "__TECH_SONAR_REVISION__"


class InstallationError(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class InstallationResult:
    pull_request: str
    warnings: tuple[str, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class LabelSpec:
    name: str
    color: str
    description: str


STATUS_LABELS: tuple[LabelSpec, ...] = (
    LabelSpec(
        "SONAR REJECT",
        "B60205",
        "Do not use this technology.",
    ),
    LabelSpec(
        "SONAR HOLD",
        "6A737D",
        "Pause adoption pending further review.",
    ),
    LabelSpec(
        "SONAR EXPLORE",
        "1D76DB",
        "Explore and evaluate this technology.",
    ),
    LabelSpec(
        "SONAR PROPOSE",
        "FBCA04",
        "Proposed for adoption; requires an open supporting PR.",
    ),
    LabelSpec(
        "SONAR ADOPT",
        "0E8A16",
        "Approved for adoption; requires a merged supporting PR.",
    ),
)


def render_workflow(revision: str) -> str:
    resource = importlib.resources.files("tech_sonar").joinpath(
        "workflows/tech-sonar.yml",
    )
    content = resource.read_text(encoding="utf-8")
    if content.count(_REVISION_MARKER) != 1:
        raise ValueError("workflow must contain exactly one revision marker")
    return content.replace(_REVISION_MARKER, revision)


def render_managed_files(revision: str) -> dict[pathlib.Path, str]:
    template = importlib.resources.files("tech_sonar").joinpath(
        "issue_templates/technology.yml",
    )
    return {
        MANAGED_WORKFLOW: render_workflow(revision),
        MANAGED_ISSUE_TEMPLATE: template.read_text(encoding="utf-8"),
    }


def render_installation_files(
    root: pathlib.Path,
    revision: str,
    owner: str,
    run: repository.CommandRunner = repository.run_command,
) -> tuple[dict[pathlib.Path, str], tuple[str, ...]]:
    managed = render_managed_files(revision)
    template_directory = root / MANAGED_ISSUE_TEMPLATE.parent
    if template_directory.exists() and any(template_directory.iterdir()):
        return managed, ()
    inherited = repository.inherited_issue_templates(owner, run)
    if inherited is None:
        del managed[MANAGED_ISSUE_TEMPLATE]
        warning = (
            "Technology issue template was not installed because "
            f"{owner}/.github could not be accessed; installing it could "
            "hide inherited issue templates."
        )
        return managed, (warning,)
    return inherited | managed, ()


def managed_files_are_current(
    root: pathlib.Path,
    contents: collections.abc.Mapping[pathlib.Path, str],
) -> bool:
    return all(
        (path := root / relative_path).exists()
        and path.read_text(encoding="utf-8") == content
        for relative_path, content in contents.items()
    )


def write_managed_files(
    root: pathlib.Path,
    contents: collections.abc.Mapping[pathlib.Path, str],
) -> None:
    for relative_path, content in contents.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def reconcile_labels(
    root: pathlib.Path,
    run: repository.CommandRunner = repository.run_command,
) -> None:
    existing = {
        name.casefold()
        for name in repository.label_names(root, run)
    }
    for label in STATUS_LABELS:
        if label.name.casefold() not in existing:
            repository.create_label(
                root,
                name=label.name,
                color=label.color,
                description=label.description,
                run=run,
            )


def unique_branch(
    root: pathlib.Path,
    now: datetime.datetime,
    suffix: collections.abc.Callable[[], str],
    run: repository.CommandRunner = repository.run_command,
) -> str:
    base = now.strftime("tech-sonar/install-%Y%m%d-%H%M%S")
    candidate = base
    while repository.branch_exists(root, candidate, run):
        candidate = f"{base}-{suffix()}"
    return candidate


def install(
    target: model.Repository,
    parent: pathlib.Path,
    source_root: pathlib.Path,
    run: repository.CommandRunner = repository.run_command,
) -> InstallationResult:
    revision = repository.source_revision(source_root, run)
    clone_root = repository.clone(target, parent / target.name, run)
    state = repository.inspect(clone_root, run)
    if (state.root / MANAGED_WORKFLOW).exists():
        raise InstallationError(
            "Tech Sonar workflow already exists; use update instead",
        )

    reconcile_labels(state.root, run)
    branch = unique_branch(
        state.root,
        datetime.datetime.now(datetime.UTC),
        lambda: secrets.token_hex(3),
        run,
    )
    repository.create_branch(state.root, branch, run)
    install_files, warnings = render_installation_files(
        state.root,
        revision,
        target.owner,
        run,
    )
    write_managed_files(state.root, install_files)
    repository.commit_and_push(
        state.root,
        "chore: install Tech Sonar",
        install_files,
        run,
    )
    pull_request = repository.open_pull_request(
        state.root,
        branch=branch,
        base=state.default_branch,
        title="Install Tech Sonar",
        body="Installs files managed by Tech Sonar.",
        run=run,
    )
    return InstallationResult(pull_request, warnings)


def update(
    target_root: pathlib.Path,
    source_root: pathlib.Path,
    run: repository.CommandRunner = repository.run_command,
) -> str | None:
    revision = repository.source_revision(source_root, run)
    state = repository.inspect(target_root, run)
    if (state.root / MANAGED_ISSUE_TEMPLATE).exists():
        managed_files = render_managed_files(revision)
    else:
        managed_files, _warnings = render_installation_files(
            state.root,
            revision,
            state.repository.owner,
            run,
        )

    reconcile_labels(state.root, run)
    if managed_files_are_current(state.root, managed_files):
        return None

    branch = state.current_branch
    if branch == state.default_branch:
        branch = unique_branch(
            state.root,
            datetime.datetime.now(datetime.UTC),
            lambda: secrets.token_hex(3),
            run,
        )
        repository.create_branch(state.root, branch, run)

    write_managed_files(state.root, managed_files)
    repository.commit_and_push(
        state.root,
        "chore: update Tech Sonar",
        managed_files,
        run,
    )
    return repository.open_pull_request(
        state.root,
        branch=branch,
        base=state.default_branch,
        title="Update Tech Sonar",
        body="Updates files managed by Tech Sonar.",
        run=run,
    )
