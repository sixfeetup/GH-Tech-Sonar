import json
import pathlib

import pytest

from tech_sonar import cli
from tech_sonar import cloudflare
from tech_sonar import installation
from tech_sonar import model
from tech_sonar import publishing


def test_parser_accepts_install_repository() -> None:
    arguments = cli.parser().parse_args(
        ["install", "sixfeetup/GH-Tech-Sonar"],
    )
    assert arguments.command == "install"
    assert arguments.repository == model.Repository(
        "sixfeetup",
        "GH-Tech-Sonar",
    )


def test_parser_rejects_invalid_install_repository(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        cli.parser().parse_args(["install", "GH-Tech-Sonar"])

    assert error.value.code == 2
    assert "repository must use OWNER/REPOSITORY form" in capsys.readouterr().err


def test_parser_accepts_pr_event_relevant_path() -> None:
    arguments = cli.parser().parse_args(
        ["pr-event-relevant", "event.json"],
    )

    assert arguments.command == "pr-event-relevant"
    assert arguments.event == pathlib.Path("event.json")


@pytest.mark.parametrize(
    ("relevant_event", "output"),
    [(True, "true\n"), (False, "false\n")],
)
def test_pr_event_relevant_prints_boolean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    relevant_event: bool,
    output: str,
) -> None:
    payload = {
        "action": "opened",
        "repository": {"full_name": "sixfeetup/sonar"},
        "pull_request": {"title": "Use #12", "body": None},
        "changes": {},
    }
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    fetched: list[tuple[model.Repository, int]] = []

    class Client:
        def __init__(self, token: str) -> None:
            assert token == "token"

        def __enter__(self) -> "Client":
            return self

        def __exit__(self, *arguments: object) -> None:
            return None

        def fetch_issue_labels(
            self,
            repository: model.Repository,
            number: int,
        ) -> tuple[model.Label, ...] | None:
            fetched.append((repository, number))
            return ()

    def is_relevant(event: object, fetch: object) -> bool:
        assert event == payload
        assert callable(fetch)
        fetch(model.Repository("sixfeetup", "sonar"), 12)
        return relevant_event

    monkeypatch.setattr(cli.auth, "resolve_token", lambda environ: "token")
    monkeypatch.setattr(cli.github, "GitHubClient", Client)
    monkeypatch.setattr(
        cli.relevance,
        "pull_request_event_is_relevant",
        is_relevant,
    )

    assert cli.main(["pr-event-relevant", str(path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == output
    assert captured.err == ""
    assert fetched == [(model.Repository("sixfeetup", "sonar"), 12)]


def test_pr_event_relevant_reports_malformed_json(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "event.json"
    path.write_text("{invalid", encoding="utf-8")

    assert cli.main(["pr-event-relevant", str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: invalid GitHub event JSON:")


def test_parser_accepts_publish_arguments() -> None:
    arguments = cli.parser().parse_args(
        [
            "publish",
            "generated/sonar.json",
            "--output",
            "built-site",
            "--args",
            'cloudflare account "Sonar Project"',
        ],
    )

    assert arguments.snapshot == pathlib.Path("generated/sonar.json")
    assert arguments.output == pathlib.Path("built-site")
    assert arguments.publisher_args == 'cloudflare account "Sonar Project"'


def test_publish_passes_parsed_arguments_and_secret(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    parsed_arguments = ("cloudflare", "account", "Sonar Project")
    parsed_values: list[str] = []
    publications: list[
        tuple[pathlib.Path, pathlib.Path, tuple[str, ...], str | None]
    ] = []

    def parse_publisher_args(value: str) -> tuple[str, ...]:
        parsed_values.append(value)
        return parsed_arguments

    def publish(
        snapshot: pathlib.Path,
        output: pathlib.Path,
        publisher_args: tuple[str, ...],
        secret: str | None,
    ) -> None:
        publications.append((snapshot, output, publisher_args, secret))

    monkeypatch.setenv("PUBLISH_SECRET", "token")
    monkeypatch.setattr(publishing, "parse_publisher_args", parse_publisher_args)
    monkeypatch.setattr(publishing, "publish", publish)

    assert cli.main(
        [
            "publish",
            "generated/sonar.json",
            "--output",
            "built-site",
            "--args",
            'cloudflare account "Sonar Project"',
        ],
    ) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert parsed_values == ['cloudflare account "Sonar Project"']
    assert publications == [
        (
            pathlib.Path("generated/sonar.json"),
            pathlib.Path("built-site"),
            parsed_arguments,
            "token",
        ),
    ]


@pytest.mark.parametrize(
    "error",
    [
        publishing.PublishingError("site assembly failed"),
        cloudflare.CloudflarePublishingError("deployment failed"),
    ],
)
def test_publish_reports_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(publishing, "publish", fail)

    result = cli.main(
        [
            "publish",
            "generated/sonar.json",
            "--output",
            "built-site",
            "--args",
            "cloudflare account project",
        ],
    )

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err == f"error: {error}\n"


def test_install_prints_pull_request_url_and_warnings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[model.Repository, pathlib.Path, pathlib.Path]] = []

    def install(
        target: model.Repository,
        parent: pathlib.Path,
        source_root: pathlib.Path,
    ) -> installation.InstallationResult:
        calls.append((target, parent, source_root))
        return installation.InstallationResult(
            "https://github.com/o/r/pull/1",
            ("Technology template was omitted.",),
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.installation, "install", install)

    assert cli.main(["install", "sixfeetup/GH-Tech-Sonar"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "https://github.com/o/r/pull/1\n"
    assert captured.err == "warning: Technology template was omitted.\n"
    assert calls == [
        (
            model.Repository("sixfeetup", "GH-Tech-Sonar"),
            tmp_path,
            pathlib.Path(cli.__file__).resolve().parents[2],
        ),
    ]


def test_update_prints_pull_request_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[pathlib.Path, pathlib.Path]] = []

    def update(
        target_root: pathlib.Path,
        source_root: pathlib.Path,
    ) -> str:
        calls.append((target_root, source_root))
        return "https://github.com/o/r/pull/1"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.installation, "update", update)

    assert cli.main(["update"]) == 0
    assert capsys.readouterr().out.endswith("/pull/1\n")
    assert calls == [
        (
            tmp_path,
            pathlib.Path(cli.__file__).resolve().parents[2],
        ),
    ]


def test_no_op_update_prints_nothing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli.installation,
        "update",
        lambda target_root, source_root: None,
    )

    assert cli.main(["update"]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize(
    ("command", "error"),
    [
        (
            ["install", "sixfeetup/GH-Tech-Sonar"],
            installation.InstallationError("installation failed"),
        ),
        (
            ["update"],
            cli.repository.RepositoryError("repository failed"),
        ),
    ],
)
def test_installation_commands_report_expected_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: list[str],
    error: Exception,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(cli.installation, command[0], fail)

    assert cli.main(command) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"error: {error}\n"


def configure_successful_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    issues: tuple[model.Issue, ...] = (),
) -> pathlib.Path:
    artifact = (tmp_path / "generated" / "sonar.json").resolve()
    artifact.parent.mkdir()
    artifact.write_text("{}\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli.repository,
        "repository_at",
        lambda path: model.Repository("sixfeetup", "GH-Tech-Sonar"),
    )
    monkeypatch.setattr(cli.auth, "resolve_token", lambda environ: "token")
    monkeypatch.setattr(
        cli.github.GitHubClient,
        "fetch_issues",
        lambda self, repository: issues,
    )
    monkeypatch.setattr(
        cli.generate,
        "utc_timestamp",
        lambda: "2026-09-15T20:30:00Z",
    )
    monkeypatch.setattr(
        cli.generate,
        "write_snapshot",
        lambda snapshot: artifact,
    )
    return artifact


def test_generate_prints_only_artifact_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact = configure_successful_generation(monkeypatch, tmp_path)

    result = cli.main(["generate"])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.out == f"{artifact}\n"
    assert captured.err == ""


def test_generate_discovers_repository_from_current_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    configure_successful_generation(monkeypatch, tmp_path)
    discovered_paths: list[pathlib.Path] = []

    def discover(path: pathlib.Path) -> model.Repository:
        discovered_paths.append(path)
        return model.Repository("sixfeetup", "GH-Tech-Sonar")

    monkeypatch.setattr(cli.repository, "repository_at", discover)

    assert cli.main(["generate"]) == 0
    assert discovered_paths == [pathlib.Path.cwd()]


def test_generate_prints_warnings_to_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    issue = model.Issue(
        number=3,
        title="Adopt a technology",
        url="https://github.com/sixfeetup/GH-Tech-Sonar/issues/3",
        state="OPEN",
        updated_at="2026-09-15T18:00:00Z",
        body_html="<p>Adopt a technology</p>",
        labels=(
            model.Label(
                name="SONAR ADOPT",
                color="ededed",
                description=None,
            ),
        ),
        pull_requests=(),
    )
    artifact = configure_successful_generation(
        monkeypatch,
        tmp_path,
        issues=(issue,),
    )

    result = cli.main(["generate"])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.out == f"{artifact}\n"
    assert "3" in captured.err
    assert "ADOPT" in captured.err
    assert "requires a merged pull request" in captured.err


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (
            cli.repository.RepositoryError("not a GitHub repository"),
            "not a GitHub repository",
        ),
        (
            cli.auth.AuthenticationError("authenticate with GitHub"),
            "authenticate with GitHub",
        ),
        (cli.github.GitHubError("GitHub unavailable"), "GitHub unavailable"),
    ],
)
def test_generate_reports_fatal_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
    expected_message: str,
) -> None:
    configure_successful_generation(monkeypatch, tmp_path)

    def fail(*args: object, **kwargs: object) -> None:
        raise error

    if isinstance(error, cli.repository.RepositoryError):
        monkeypatch.setattr(cli.repository, "repository_at", fail)
    elif isinstance(error, cli.auth.AuthenticationError):
        monkeypatch.setattr(cli.auth, "resolve_token", fail)
    else:
        monkeypatch.setattr(cli.github.GitHubClient, "fetch_issues", fail)

    result = cli.main(["generate"])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err.startswith("error: ")
    assert expected_message in captured.err


def test_generate_reports_artifact_write_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_successful_generation(monkeypatch, tmp_path)

    def fail(snapshot: model.Snapshot) -> pathlib.Path:
        raise OSError("disk full")

    monkeypatch.setattr(cli.generate, "write_snapshot", fail)

    result = cli.main(["generate"])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err.startswith("error: ")
    assert "disk full" in captured.err
