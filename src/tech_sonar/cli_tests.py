import pathlib

import pytest

from tech_sonar import cli
from tech_sonar import model


def configure_successful_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    issues: tuple[model.Issue, ...] = (),
) -> pathlib.Path:
    config_path = tmp_path / "sonar.toml"
    config_path.write_text('repository = "sixfeetup/GH-Tech-Sonar"\n')
    artifact = (tmp_path / "generated" / "sonar.json").resolve()
    artifact.parent.mkdir()
    artifact.write_text("{}\n")

    monkeypatch.chdir(tmp_path)
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
        (cli.config.ConfigError("invalid repository"), "invalid repository"),
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

    if isinstance(error, cli.config.ConfigError):
        monkeypatch.setattr(cli.config, "load_config", fail)
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
