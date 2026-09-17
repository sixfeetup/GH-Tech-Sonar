import pathlib

from tech_sonar import installation


EXPECTED_LABELS = {
    "SONAR REJECT": ("B60205", "Do not use this technology."),
    "SONAR HOLD": ("6A737D", "Pause adoption pending further review."),
    "SONAR EXPLORE": ("1D76DB", "Explore and evaluate this technology."),
    "SONAR PROPOSE": (
        "FBCA04",
        "Proposed for adoption; requires an open supporting PR.",
    ),
    "SONAR ADOPT": (
        "0E8A16",
        "Approved for adoption; requires a merged supporting PR.",
    ),
}


def test_status_labels_match_specification() -> None:
    assert {
        label.name: (label.color, label.description)
        for label in installation.STATUS_LABELS
    } == EXPECTED_LABELS


def test_reconcile_labels_creates_only_missing_names(
    tmp_path: pathlib.Path,
) -> None:
    calls: list[tuple[tuple[str, ...], pathlib.Path | None]] = []

    def run(
        arguments: tuple[str, ...],
        cwd: pathlib.Path | None,
    ) -> str:
        calls.append((arguments, cwd))
        if arguments[:3] == ("gh", "label", "list"):
            return "sonar reject\nSonar Hold\n"
        return ""

    installation.reconcile_labels(tmp_path, run)

    assert calls == [
        (
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
            tmp_path,
        ),
        *[
            (
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
                tmp_path,
            )
            for name, (color, description) in list(EXPECTED_LABELS.items())[2:]
        ],
    ]


def test_render_workflow_replaces_revision_marker() -> None:
    workflow = installation.render_workflow("abc123")

    assert "__TECH_SONAR_REVISION__" not in workflow
    assert workflow.count("abc123") == 1
    assert workflow.endswith("\n")
    for expected in (
        "workflow_dispatch",
        "issues",
        "pull_request",
        "concurrency",
        "cancel-in-progress: false",
        "permissions",
        "astral-sh/setup-uv@v6",
        "tech-sonar generate",
    ):
        assert expected in workflow


def test_workflow_is_current_uses_exact_file_comparison(
    tmp_path: pathlib.Path,
) -> None:
    content = "workflow\n"

    assert not installation.workflow_is_current(tmp_path, content)

    managed_workflow = tmp_path / installation.MANAGED_WORKFLOW
    managed_workflow.parent.mkdir(parents=True)
    managed_workflow.write_text(content, encoding="utf-8")

    assert installation.workflow_is_current(tmp_path, content)
    assert not installation.workflow_is_current(tmp_path, "workflow")


def test_write_workflow_creates_parents_and_writes_exact_text(
    tmp_path: pathlib.Path,
) -> None:
    content = "workflow\n"

    installation.write_workflow(tmp_path, content)

    assert (tmp_path / installation.MANAGED_WORKFLOW).read_text(
        encoding="utf-8",
    ) == content
