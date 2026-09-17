import dataclasses
import importlib.resources
import pathlib

from tech_sonar import repository


MANAGED_WORKFLOW = pathlib.Path(".github/workflows/tech-sonar.yml")
_REVISION_MARKER = "__TECH_SONAR_REVISION__"


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


def workflow_is_current(root: pathlib.Path, content: str) -> bool:
    workflow = root / MANAGED_WORKFLOW
    if not workflow.exists():
        return False
    return workflow.read_text(encoding="utf-8") == content


def write_workflow(root: pathlib.Path, content: str) -> None:
    workflow = root / MANAGED_WORKFLOW
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(content, encoding="utf-8")


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
