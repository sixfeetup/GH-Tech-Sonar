import datetime
import pathlib

import pytest

from tech_sonar import installation
from tech_sonar import model
from tech_sonar import repository


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


def test_render_managed_files_includes_technology_issue_form() -> None:
    files = installation.render_managed_files("abc123")

    template = files[installation.MANAGED_ISSUE_TEMPLATE]
    assert "name: 🔭 Technology" in template
    assert "  - SONAR EXPLORE" in template
    assert "SONAR CATEGORY …" in template
    assert "replace" in template
    assert "`SONAR EXPLORE` with another Sonar status" in template
    assert "label: Description" in template
    assert "label: Suitable projects" in template
    assert "label: Required skills" in template


def test_render_workflow_replaces_revision_marker() -> None:
    workflow = installation.render_workflow("abc123")

    assert "__TECH_SONAR_REVISION__" not in workflow
    assert workflow.count("abc123") == 1
    assert workflow.endswith("\n")
    assert "workflow_dispatch" in workflow
    assert "issues" in workflow
    assert "pull_request" in workflow
    assert "concurrency" in workflow
    assert "cancel-in-progress: false" in workflow
    for expected in (
        "actions/setup-node@v4",
        "node-version: 22",
        "PUBLISH_ARGS: ${{ vars.PUBLISH_ARGS }}",
        "PUBLISH_SECRET: ${{ secrets.PUBLISH_SECRET }}",
        'tech-sonar publish "${{ steps.generate.outputs.artifact }}"',
        '--output "$RUNNER_TEMP/tech-sonar-site"',
        '--args "$PUBLISH_ARGS"',
        "always()",
        "name: tech-sonar-site",
        "path: ${{ runner.temp }}/tech-sonar-site",
        "retention-days: 1",
    ):
        assert expected in workflow

    assert "tech-sonar-json" not in workflow


def test_render_workflow_filters_irrelevant_events() -> None:
    workflow = installation.render_workflow("abc123")

    assert "      - synchronize\n" not in workflow
    assert "github.event.changes.title != null" in workflow
    assert "github.event.changes.body != null" in workflow
    assert "github.event.issue.labels.*.name" in workflow
    assert "github.event.label.name == 'SONAR EXPLORE'" in workflow
    assert "name: Determine PR relevance" in workflow
    assert 'tech-sonar pr-event-relevant "$GITHUB_EVENT_PATH"' in workflow
    assert "steps.pr-relevance.outputs.relevant == 'true'" in workflow
    for status in EXPECTED_LABELS:
        assert status in workflow
    for expected in (
        "concurrency",
        "cancel-in-progress: false",
        "name: Generate Tech Sonar data",
        "id: generate",
        "tech-sonar generate",
        "name: Build and publish Tech Sonar",
        'tech-sonar publish "${{ steps.generate.outputs.artifact }}"',
        "name: Upload assembled site for debugging",
        "always()",
        "actions/upload-artifact@v4",
    ):
        assert expected in workflow


def test_managed_files_are_current_uses_exact_file_comparison(
    tmp_path: pathlib.Path,
) -> None:
    contents = {
        installation.MANAGED_WORKFLOW: "workflow\n",
        installation.MANAGED_ISSUE_TEMPLATE: "template\n",
    }

    assert not installation.managed_files_are_current(tmp_path, contents)

    installation.write_managed_files(tmp_path, contents)

    assert installation.managed_files_are_current(tmp_path, contents)
    contents[installation.MANAGED_ISSUE_TEMPLATE] = "changed\n"
    assert not installation.managed_files_are_current(tmp_path, contents)


def test_write_managed_files_creates_parents_and_writes_exact_text(
    tmp_path: pathlib.Path,
) -> None:
    contents = {
        installation.MANAGED_WORKFLOW: "workflow\n",
        installation.MANAGED_ISSUE_TEMPLATE: "template\n",
    }

    installation.write_managed_files(tmp_path, contents)

    for path, content in contents.items():
        assert (tmp_path / path).read_text(encoding="utf-8") == content


def test_install_orchestrates_repository_changes_in_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    target = model.Repository("sixfeetup", "example")
    source_root = tmp_path / "source"
    clone_root = tmp_path / target.name
    state = repository.State(
        root=clone_root,
        repository=target,
        default_branch="main",
        current_branch="main",
    )
    calls: list[str] = []

    def source_revision(
        root: pathlib.Path,
        run: repository.CommandRunner,
    ) -> str:
        assert root == source_root
        calls.append("source_revision")
        return "abc123"

    def clone(
        requested: model.Repository,
        destination: pathlib.Path,
        run: repository.CommandRunner,
    ) -> pathlib.Path:
        assert requested == target
        assert destination == clone_root
        destination.mkdir()
        calls.append("clone")
        return destination

    def inspect(
        root: pathlib.Path,
        run: repository.CommandRunner,
    ) -> repository.State:
        assert root == clone_root
        calls.append("inspect")
        return state

    def reconcile_labels(
        root: pathlib.Path,
        run: repository.CommandRunner,
    ) -> None:
        assert root == clone_root
        calls.append("reconcile_labels")

    def unique_branch(
        root: pathlib.Path,
        now: datetime.datetime,
        suffix: object,
        run: repository.CommandRunner,
    ) -> str:
        assert root == clone_root
        assert now.tzinfo == datetime.UTC
        assert callable(suffix)
        calls.append("unique_branch")
        return "tech-sonar/install-20260102-030405"

    def create_branch(
        root: pathlib.Path,
        branch: str,
        run: repository.CommandRunner,
    ) -> None:
        assert (root, branch) == (
            clone_root,
            "tech-sonar/install-20260102-030405",
        )
        calls.append("create_branch")

    def write_managed_files(
        root: pathlib.Path,
        contents: dict[pathlib.Path, str],
    ) -> None:
        assert root == clone_root
        assert tuple(contents) == (
            installation.MANAGED_WORKFLOW,
            installation.MANAGED_ISSUE_TEMPLATE,
        )
        assert "abc123" in contents[installation.MANAGED_WORKFLOW]
        calls.append("write_managed_files")

    def commit_and_push(
        root: pathlib.Path,
        message: str,
        managed_paths: object,
        run: repository.CommandRunner,
    ) -> None:
        assert root == clone_root
        assert message == "chore: install Tech Sonar"
        assert tuple(managed_paths) == (
            installation.MANAGED_WORKFLOW,
            installation.MANAGED_ISSUE_TEMPLATE,
        )
        calls.append("commit_and_push")

    def open_pull_request(
        root: pathlib.Path,
        *,
        branch: str,
        base: str,
        title: str,
        body: str,
        run: repository.CommandRunner,
    ) -> str:
        assert root == clone_root
        assert branch == "tech-sonar/install-20260102-030405"
        assert base == "main"
        assert title == "Install Tech Sonar"
        assert body == "Installs files managed by Tech Sonar."
        calls.append("open_pull_request")
        return "https://github.com/sixfeetup/example/pull/1"

    monkeypatch.setattr(installation.repository, "source_revision", source_revision)
    monkeypatch.setattr(installation.repository, "clone", clone)
    monkeypatch.setattr(installation.repository, "inspect", inspect)
    monkeypatch.setattr(installation, "reconcile_labels", reconcile_labels)
    monkeypatch.setattr(installation, "unique_branch", unique_branch)
    monkeypatch.setattr(installation.repository, "create_branch", create_branch)
    monkeypatch.setattr(
        installation,
        "write_managed_files",
        write_managed_files,
    )
    monkeypatch.setattr(
        installation.repository,
        "commit_and_push",
        commit_and_push,
    )
    monkeypatch.setattr(
        installation.repository,
        "open_pull_request",
        open_pull_request,
    )

    result = installation.install(
        target,
        tmp_path,
        source_root,
        run=lambda arguments, cwd: "",
    )

    assert result == "https://github.com/sixfeetup/example/pull/1"
    assert calls == [
        "source_revision",
        "clone",
        "inspect",
        "reconcile_labels",
        "unique_branch",
        "create_branch",
        "write_managed_files",
        "commit_and_push",
        "open_pull_request",
    ]


def test_install_refuses_existing_workflow_before_labels(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    target = model.Repository("sixfeetup", "example")
    clone_root = tmp_path / target.name
    calls: list[str] = []

    monkeypatch.setattr(
        installation.repository,
        "source_revision",
        lambda root, run: "abc123",
    )

    def clone(
        requested: model.Repository,
        destination: pathlib.Path,
        run: repository.CommandRunner,
    ) -> pathlib.Path:
        destination.mkdir()
        managed_path = destination / installation.MANAGED_WORKFLOW
        managed_path.parent.mkdir(parents=True)
        managed_path.write_text("existing\n", encoding="utf-8")
        return destination

    monkeypatch.setattr(installation.repository, "clone", clone)
    monkeypatch.setattr(
        installation.repository,
        "inspect",
        lambda root, run: repository.State(
            root=root,
            repository=target,
            default_branch="main",
            current_branch="main",
        ),
    )
    monkeypatch.setattr(
        installation,
        "reconcile_labels",
        lambda root, run: calls.append("reconcile_labels"),
    )

    with pytest.raises(installation.InstallationError, match="update"):
        installation.install(
            target,
            tmp_path,
            tmp_path / "source",
            run=lambda arguments, cwd: "",
        )

    assert calls == []


def test_install_unique_branch_adds_suffix_only_on_collision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    existing: set[str] = set()
    suffix_calls = 0

    def branch_exists(
        root: pathlib.Path,
        branch: str,
        run: repository.CommandRunner,
    ) -> bool:
        return branch in existing

    def suffix() -> str:
        nonlocal suffix_calls
        suffix_calls += 1
        return "a1b2c3"

    monkeypatch.setattr(installation.repository, "branch_exists", branch_exists)
    now = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)

    branch = installation.unique_branch(
        tmp_path,
        now,
        suffix,
        run=lambda arguments, cwd: "",
    )

    assert branch == "tech-sonar/install-20260102-030405"
    assert suffix_calls == 0

    existing.add(branch)
    assert installation.unique_branch(
        tmp_path,
        now,
        suffix,
        run=lambda arguments, cwd: "",
    ) == "tech-sonar/install-20260102-030405-a1b2c3"
    assert suffix_calls == 1


def test_unique_branch_retries_when_suffixed_candidate_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    checked: list[str] = []
    existing = {
        "tech-sonar/install-20260102-030405",
        "tech-sonar/install-20260102-030405-a1b2c3",
    }
    suffixes = iter(("a1b2c3", "d4e5f6"))

    def branch_exists(
        root: pathlib.Path,
        branch: str,
        run: repository.CommandRunner,
    ) -> bool:
        checked.append(branch)
        return branch in existing

    monkeypatch.setattr(installation.repository, "branch_exists", branch_exists)

    branch = installation.unique_branch(
        tmp_path,
        datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.UTC),
        lambda: next(suffixes),
        run=lambda arguments, cwd: "",
    )

    assert branch == "tech-sonar/install-20260102-030405-d4e5f6"
    assert checked == [
        "tech-sonar/install-20260102-030405",
        "tech-sonar/install-20260102-030405-a1b2c3",
        "tech-sonar/install-20260102-030405-d4e5f6",
    ]


def test_update_reconciles_labels_before_canonical_no_op(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    target_root.mkdir()
    canonical = {
        installation.MANAGED_WORKFLOW: "canonical abc123\n",
        installation.MANAGED_ISSUE_TEMPLATE: "template\n",
    }
    installation.write_managed_files(target_root, canonical)
    calls: list[str] = []

    def source_revision(root: pathlib.Path, run: repository.CommandRunner) -> str:
        assert root == source_root
        calls.append("source_revision")
        return "abc123"

    def inspect(
        root: pathlib.Path,
        run: repository.CommandRunner,
    ) -> repository.State:
        assert root == target_root
        calls.append("inspect")
        return repository.State(
            root=target_root,
            repository=model.Repository("sixfeetup", "example"),
            default_branch="main",
            current_branch="main",
        )

    monkeypatch.setattr(installation.repository, "source_revision", source_revision)
    monkeypatch.setattr(installation.repository, "inspect", inspect)
    monkeypatch.setattr(
        installation,
        "render_managed_files",
        lambda revision: canonical,
    )
    monkeypatch.setattr(
        installation,
        "reconcile_labels",
        lambda root, run: calls.append("reconcile_labels"),
    )
    monkeypatch.setattr(
        installation.repository,
        "create_branch",
        lambda *args: pytest.fail("no-op update created a branch"),
    )
    monkeypatch.setattr(
        installation.repository,
        "open_pull_request",
        lambda *args, **kwargs: pytest.fail("no-op update opened a PR"),
    )

    result = installation.update(
        target_root,
        source_root,
        run=lambda arguments, cwd: "",
    )

    assert result is None
    for path, content in canonical.items():
        assert (target_root / path).read_text(encoding="utf-8") == content
    assert calls == [
        "source_revision",
        "inspect",
        "reconcile_labels",
    ]


def test_update_default_branch_creates_branch_before_writing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    target_root.mkdir()
    canonical = {
        installation.MANAGED_WORKFLOW: "canonical abc123\n",
        installation.MANAGED_ISSUE_TEMPLATE: "template\n",
    }
    branch = "tech-sonar/install-20260102-030405"
    calls: list[str] = []
    original_write_managed_files = installation.write_managed_files

    monkeypatch.setattr(
        installation.repository,
        "source_revision",
        lambda root, run: calls.append("source_revision") or "abc123",
    )
    monkeypatch.setattr(
        installation.repository,
        "inspect",
        lambda root, run: calls.append("inspect")
        or repository.State(
            root=target_root,
            repository=model.Repository("sixfeetup", "example"),
            default_branch="main",
            current_branch="main",
        ),
    )
    monkeypatch.setattr(
        installation,
        "render_managed_files",
        lambda revision: canonical,
    )
    monkeypatch.setattr(
        installation,
        "reconcile_labels",
        lambda root, run: calls.append("reconcile_labels"),
    )
    monkeypatch.setattr(
        installation,
        "unique_branch",
        lambda root, now, suffix, run: calls.append("unique_branch") or branch,
    )
    monkeypatch.setattr(
        installation.repository,
        "create_branch",
        lambda root, name, run: calls.append("create_branch"),
    )

    def write_managed_files(
        root: pathlib.Path,
        contents: dict[pathlib.Path, str],
    ) -> None:
        calls.append("write_managed_files")
        original_write_managed_files(root, contents)

    monkeypatch.setattr(
        installation,
        "write_managed_files",
        write_managed_files,
    )

    def commit_and_push(
        root: pathlib.Path,
        message: str,
        managed_paths: object,
        run: repository.CommandRunner,
    ) -> None:
        assert message == "chore: update Tech Sonar"
        assert tuple(managed_paths) == tuple(canonical)
        calls.append("commit_and_push")

    monkeypatch.setattr(
        installation.repository,
        "commit_and_push",
        commit_and_push,
    )

    def open_pull_request(
        root: pathlib.Path,
        *,
        branch: str,
        base: str,
        title: str,
        body: str,
        run: repository.CommandRunner,
    ) -> str:
        assert branch == "tech-sonar/install-20260102-030405"
        assert base == "main"
        assert title == "Update Tech Sonar"
        assert body == "Updates files managed by Tech Sonar."
        calls.append("open_pull_request")
        return "https://github.com/sixfeetup/example/pull/2"

    monkeypatch.setattr(
        installation.repository,
        "open_pull_request",
        open_pull_request,
    )

    result = installation.update(
        target_root,
        source_root,
        run=lambda arguments, cwd: "",
    )

    assert result == "https://github.com/sixfeetup/example/pull/2"
    for path, content in canonical.items():
        assert (target_root / path).read_text(encoding="utf-8") == content
    assert calls == [
        "source_revision",
        "inspect",
        "reconcile_labels",
        "unique_branch",
        "create_branch",
        "write_managed_files",
        "commit_and_push",
        "open_pull_request",
    ]


def test_update_non_default_branch_writes_without_creating_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    target_root = tmp_path / "target"
    target_root.mkdir()
    canonical = {
        installation.MANAGED_WORKFLOW: "canonical abc123\n",
        installation.MANAGED_ISSUE_TEMPLATE: "template\n",
    }
    calls: list[str] = []
    original_write_managed_files = installation.write_managed_files

    monkeypatch.setattr(
        installation.repository,
        "source_revision",
        lambda root, run: calls.append("source_revision") or "abc123",
    )
    monkeypatch.setattr(
        installation.repository,
        "inspect",
        lambda root, run: calls.append("inspect")
        or repository.State(
            root=target_root,
            repository=model.Repository("sixfeetup", "example"),
            default_branch="main",
            current_branch="topic",
        ),
    )
    monkeypatch.setattr(
        installation,
        "render_managed_files",
        lambda revision: canonical,
    )
    monkeypatch.setattr(
        installation,
        "reconcile_labels",
        lambda root, run: calls.append("reconcile_labels"),
    )
    monkeypatch.setattr(
        installation.repository,
        "create_branch",
        lambda *args: pytest.fail("non-default update created a branch"),
    )

    def write_managed_files(
        root: pathlib.Path,
        contents: dict[pathlib.Path, str],
    ) -> None:
        calls.append("write_managed_files")
        original_write_managed_files(root, contents)

    monkeypatch.setattr(
        installation,
        "write_managed_files",
        write_managed_files,
    )
    monkeypatch.setattr(
        installation.repository,
        "commit_and_push",
        lambda root, message, managed_paths, run: calls.append(
            "commit_and_push",
        ),
    )

    def open_pull_request(
        root: pathlib.Path,
        *,
        branch: str,
        base: str,
        title: str,
        body: str,
        run: repository.CommandRunner,
    ) -> str:
        assert branch == "topic"
        calls.append("open_pull_request")
        return "https://github.com/sixfeetup/example/pull/3"

    monkeypatch.setattr(
        installation.repository,
        "open_pull_request",
        open_pull_request,
    )

    assert installation.update(
        target_root,
        tmp_path / "source",
        run=lambda arguments, cwd: "",
    ) == "https://github.com/sixfeetup/example/pull/3"
    assert calls == [
        "source_revision",
        "inspect",
        "reconcile_labels",
        "write_managed_files",
        "commit_and_push",
        "open_pull_request",
    ]


def test_update_returns_existing_open_pull_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    target_root = tmp_path / "target"
    target_root.mkdir()
    commands: list[tuple[str, ...]] = []
    existing_url = "https://github.com/sixfeetup/example/pull/4"

    monkeypatch.setattr(
        installation.repository,
        "source_revision",
        lambda root, run: "abc123",
    )
    monkeypatch.setattr(
        installation.repository,
        "inspect",
        lambda root, run: repository.State(
            root=target_root,
            repository=model.Repository("sixfeetup", "example"),
            default_branch="main",
            current_branch="topic",
        ),
    )
    monkeypatch.setattr(
        installation,
        "render_managed_files",
        lambda revision: {
            installation.MANAGED_WORKFLOW: "canonical abc123\n",
            installation.MANAGED_ISSUE_TEMPLATE: "template\n",
        },
    )
    monkeypatch.setattr(installation, "reconcile_labels", lambda root, run: None)
    monkeypatch.setattr(
        installation.repository,
        "commit_and_push",
        lambda root, message, managed_paths, run: None,
    )

    def run(arguments: tuple[str, ...], cwd: pathlib.Path | None) -> str:
        commands.append(arguments)
        if arguments[:3] == ("gh", "pr", "list"):
            return existing_url
        pytest.fail(f"unexpected command: {arguments}")

    assert installation.update(
        target_root,
        tmp_path / "source",
        run=run,
    ) == existing_url
    assert len(commands) == 1
    assert commands[0][:3] == ("gh", "pr", "list")


def test_update_dirty_target_fails_before_labels_or_files_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    target_root = tmp_path / "target"
    target_root.mkdir()
    calls: list[str] = []

    monkeypatch.setattr(
        installation.repository,
        "source_revision",
        lambda root, run: calls.append("source_revision") or "abc123",
    )

    def inspect(
        root: pathlib.Path,
        run: repository.CommandRunner,
    ) -> repository.State:
        calls.append("inspect")
        raise repository.RepositoryError("repository worktree is not clean")

    monkeypatch.setattr(installation.repository, "inspect", inspect)
    monkeypatch.setattr(
        installation,
        "reconcile_labels",
        lambda root, run: calls.append("reconcile_labels"),
    )

    with pytest.raises(repository.RepositoryError, match="not clean"):
        installation.update(
            target_root,
            tmp_path / "source",
            run=lambda arguments, cwd: "",
        )

    assert calls == ["source_revision", "inspect"]
    assert not (target_root / installation.MANAGED_WORKFLOW).exists()
    assert not (target_root / installation.MANAGED_ISSUE_TEMPLATE).exists()


def test_update_dirty_source_fails_before_target_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    target_root = tmp_path / "target"
    target_root.mkdir()
    calls: list[str] = []

    def source_revision(
        root: pathlib.Path,
        run: repository.CommandRunner,
    ) -> str:
        calls.append("source_revision")
        raise repository.RepositoryError("repository worktree is not clean")

    monkeypatch.setattr(installation.repository, "source_revision", source_revision)
    monkeypatch.setattr(
        installation.repository,
        "inspect",
        lambda root, run: calls.append("inspect"),
    )
    monkeypatch.setattr(
        installation,
        "reconcile_labels",
        lambda root, run: calls.append("reconcile_labels"),
    )

    with pytest.raises(repository.RepositoryError, match="not clean"):
        installation.update(
            target_root,
            tmp_path / "source",
            run=lambda arguments, cwd: "",
        )

    assert calls == ["source_revision"]
    assert not (target_root / installation.MANAGED_WORKFLOW).exists()
    assert not (target_root / installation.MANAGED_ISSUE_TEMPLATE).exists()


def test_update_keeps_created_labels_when_later_git_operation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    target_root = tmp_path / "target"
    target_root.mkdir()
    created_labels: list[str] = []

    monkeypatch.setattr(
        installation.repository,
        "source_revision",
        lambda root, run: "abc123",
    )
    monkeypatch.setattr(
        installation.repository,
        "inspect",
        lambda root, run: repository.State(
            root=target_root,
            repository=model.Repository("sixfeetup", "example"),
            default_branch="main",
            current_branch="main",
        ),
    )
    monkeypatch.setattr(
        installation,
        "render_managed_files",
        lambda revision: {
            installation.MANAGED_WORKFLOW: "canonical abc123\n",
            installation.MANAGED_ISSUE_TEMPLATE: "template\n",
        },
    )
    monkeypatch.setattr(
        installation.repository,
        "label_names",
        lambda root, run: frozenset(),
    )
    monkeypatch.setattr(
        installation.repository,
        "create_label",
        lambda root, *, name, color, description, run: created_labels.append(name),
    )
    monkeypatch.setattr(
        installation,
        "unique_branch",
        lambda root, now, suffix, run: "tech-sonar/install-20260102-030405",
    )

    def create_branch(
        root: pathlib.Path,
        branch: str,
        run: repository.CommandRunner,
    ) -> None:
        raise repository.RepositoryError("git switch failed")

    monkeypatch.setattr(installation.repository, "create_branch", create_branch)

    with pytest.raises(repository.RepositoryError, match="git switch failed"):
        installation.update(
            target_root,
            tmp_path / "source",
            run=lambda arguments, cwd: "",
        )

    assert created_labels == list(EXPECTED_LABELS)
    assert not (target_root / installation.MANAGED_WORKFLOW).exists()
