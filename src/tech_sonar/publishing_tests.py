import pathlib
import shutil
import subprocess

import pytest

from tech_sonar import publishing


def make_web_source(tmp_path: pathlib.Path) -> pathlib.Path:
    web_source = tmp_path / "web-source"
    public = web_source / "public"
    public.mkdir(parents=True)
    (public / "sonar.json").write_text("old fixture")
    (web_source / "package.json").write_text("{}")
    (web_source / "package-lock.json").write_text("{}")
    return web_source


def test_parse_publisher_args_handles_absent_and_empty_values() -> None:
    assert publishing.parse_publisher_args(None) == ()
    assert publishing.parse_publisher_args("  \t\n") == ()


def test_parse_publisher_args_supports_shell_quoting() -> None:
    assert publishing.parse_publisher_args(
        'cloudflare account-123 "Sonar Project"',
    ) == (
        "cloudflare",
        "account-123",
        "Sonar Project",
    )


def test_parse_publisher_args_rejects_unmatched_quoting() -> None:
    with pytest.raises(
        publishing.PublishingError,
        match="^invalid PUBLISH_ARGS:",
    ):
        publishing.parse_publisher_args('cloudflare account-123 "project')


def test_publish_rejects_unsupported_publisher(
    tmp_path: pathlib.Path,
) -> None:
    snapshot = tmp_path / "sonar.json"
    output = tmp_path / "site"

    with pytest.raises(
        publishing.PublishingError,
        match="unsupported publisher: unknown",
    ):
        publishing.publish(snapshot, output, ("unknown",), "secret")


@pytest.mark.parametrize(
    "value",
    [
        "cloudflare account",
        'cloudflare "" project',
        'cloudflare account ""',
    ],
)
def test_publish_rejects_invalid_cloudflare_arguments(
    tmp_path: pathlib.Path,
    value: str,
) -> None:
    snapshot = tmp_path / "sonar.json"
    output = tmp_path / "site"

    with pytest.raises(
        publishing.PublishingError,
        match="cloudflare requires an account ID and project",
    ):
        publishing.publish(
            snapshot,
            output,
            publishing.parse_publisher_args(value),
            "secret",
        )


def test_publish_assembles_site_and_dispatches_cloudflare(
    tmp_path: pathlib.Path,
) -> None:
    web_source = make_web_source(tmp_path)
    snapshot = tmp_path / "sonar.json"
    snapshot.write_text('{"items": []}')
    output = tmp_path / "site"
    commands: list[tuple[tuple[str, ...], pathlib.Path]] = []
    deployments: list[tuple[pathlib.Path, pathlib.Path, str, str, str]] = []

    def run(arguments: tuple[str, ...], cwd: pathlib.Path) -> None:
        commands.append((arguments, cwd))
        if arguments == ("npm", "run", "build"):
            dist = cwd / "dist"
            dist.mkdir()
            (dist / "index.html").write_text("Tech Sonar")
            shutil.copyfile(cwd / "public" / "sonar.json", dist / "sonar.json")

    def deploy(
        site_directory: pathlib.Path,
        npm_root: pathlib.Path,
        account_id: str,
        project: str,
        secret: str,
    ) -> None:
        deployments.append(
            (site_directory, npm_root, account_id, project, secret),
        )

    publishing.publish(
        snapshot,
        output,
        ("cloudflare", "account-123", "project"),
        "secret",
        web_source=web_source,
        run=run,
        deploy=deploy,
    )

    workspace = commands[0][1]
    assert commands == [
        (("npm", "ci"), workspace),
        (("npm", "run", "build"), workspace),
    ]
    assert (output / "index.html").read_text() == "Tech Sonar"
    assert (output / "sonar.json").read_text() == snapshot.read_text()
    assert deployments == [
        (output, workspace, "account-123", "project", "secret"),
    ]


def test_existing_output_prevents_cloudflare_dispatch(
    tmp_path: pathlib.Path,
) -> None:
    web_source = make_web_source(tmp_path)
    snapshot = tmp_path / "sonar.json"
    output = tmp_path / "site"
    output.mkdir()
    deployments: list[object] = []

    with pytest.raises(
        publishing.PublishingError,
        match=f"output directory already exists: {output}",
    ):
        publishing.publish(
            snapshot,
            output,
            ("cloudflare", "account-123", "project"),
            "secret",
            web_source=web_source,
            deploy=lambda *arguments: deployments.append(arguments),
        )

    assert deployments == []


def test_missing_secret_prevents_cloudflare_dispatch(
    tmp_path: pathlib.Path,
) -> None:
    web_source = make_web_source(tmp_path)
    snapshot = tmp_path / "sonar.json"
    output = tmp_path / "site"
    deployments: list[object] = []

    with pytest.raises(
        publishing.PublishingError,
        match="PUBLISH_SECRET is required",
    ):
        publishing.publish(
            snapshot,
            output,
            ("cloudflare", "account-123", "project"),
            None,
            web_source=web_source,
            deploy=lambda *arguments: deployments.append(arguments),
        )

    assert deployments == []


def test_missing_publisher_args_prevents_cloudflare_dispatch(
    tmp_path: pathlib.Path,
) -> None:
    deployments: list[object] = []

    with pytest.raises(
        publishing.PublishingError,
        match="PUBLISH_ARGS is required",
    ):
        publishing.publish(
            tmp_path / "sonar.json",
            tmp_path / "site",
            (),
            "secret",
            web_source=make_web_source(tmp_path),
            deploy=lambda *arguments: deployments.append(arguments),
        )

    assert deployments == []


def test_build_failure_prevents_cloudflare_dispatch(
    tmp_path: pathlib.Path,
) -> None:
    web_source = make_web_source(tmp_path)
    snapshot = tmp_path / "sonar.json"
    snapshot.write_text("{}")
    deployments: list[object] = []

    def fail(arguments: tuple[str, ...], cwd: pathlib.Path) -> None:
        raise publishing.PublishingError("npm failed")

    with pytest.raises(publishing.PublishingError, match="npm failed"):
        publishing.publish(
            snapshot,
            tmp_path / "site",
            ("cloudflare", "account-123", "project"),
            "secret",
            web_source=web_source,
            run=fail,
            deploy=lambda *arguments: deployments.append(arguments),
        )

    assert deployments == []


def test_run_command_translates_os_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("npm missing")

    monkeypatch.setattr(subprocess, "run", fail)

    with pytest.raises(publishing.PublishingError, match="npm failed: npm missing"):
        publishing.run_command(("npm", "ci"), tmp_path)


def test_run_command_includes_stderr_without_a_secret(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "token-456"
    child_environment: dict[str, str] = {}
    monkeypatch.setenv("PUBLISH_SECRET", secret)

    def fail(*args: object, **kwargs: object) -> None:
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        child_environment.update(environment)
        visible_secret = environment.get(
            "PUBLISH_SECRET",
            "publishing secret unavailable",
        )
        raise subprocess.CalledProcessError(
            1,
            ("npm", "ci"),
            stderr=f"dependency installation failed: {visible_secret}\n",
        )

    monkeypatch.setattr(subprocess, "run", fail)

    with pytest.raises(publishing.PublishingError) as error:
        publishing.run_command(("npm", "ci"), tmp_path)

    assert str(error.value) == (
        "npm failed: dependency installation failed: "
        "publishing secret unavailable"
    )
    assert "PUBLISH_SECRET" not in child_environment
    assert secret not in str(error.value)


def test_snapshot_filesystem_failure_names_the_path(
    tmp_path: pathlib.Path,
) -> None:
    snapshot = tmp_path / "missing.json"

    with pytest.raises(publishing.PublishingError) as error:
        publishing.publish(
            snapshot,
            tmp_path / "site",
            ("cloudflare", "account-123", "project"),
            "secret",
            web_source=make_web_source(tmp_path),
        )

    assert str(snapshot) in str(error.value)
    assert "No such file or directory" in str(error.value)
