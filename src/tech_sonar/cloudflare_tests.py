import pathlib
import subprocess

import pytest

from tech_sonar import cloudflare


def test_publish_uses_locked_wrangler_and_translates_environment(
    tmp_path: pathlib.Path,
) -> None:
    calls: list[
        tuple[tuple[str, ...], pathlib.Path, dict[str, str]]
    ] = []
    site = tmp_path / "site"
    npm_root = tmp_path / "web"

    cloudflare.publish(
        site,
        npm_root,
        account_id="account-123",
        project="tech-sonar",
        secret="token-456",
        environ={"PATH": "/bin", "PUBLISH_SECRET": "token-456"},
        run=lambda arguments, cwd, environ: calls.append(
            (arguments, cwd, dict(environ)),
        ),
    )

    assert calls == [
        (
            (
                "npm",
                "exec",
                "wrangler",
                "pages",
                "deploy",
                str(site),
                "--project-name",
                "tech-sonar",
            ),
            npm_root,
            {
                "PATH": "/bin",
                "CLOUDFLARE_ACCOUNT_ID": "account-123",
                "CLOUDFLARE_API_TOKEN": "token-456",
            },
        ),
    ]


def test_run_command_translates_os_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("wrangler missing")

    monkeypatch.setattr(subprocess, "run", fail)

    with pytest.raises(cloudflare.CloudflarePublishingError) as error:
        cloudflare.run_command(
            ("npm", "exec", "wrangler"),
            tmp_path,
            {},
        )

    assert str(error.value) == "Wrangler failed: wrangler missing"


def test_run_command_translates_called_process_error(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments = ("npm", "exec", "wrangler")

    def fail(*args: object, **kwargs: object) -> None:
        raise subprocess.CalledProcessError(
            1,
            arguments,
            stderr="deployment rejected\n",
        )

    monkeypatch.setattr(subprocess, "run", fail)

    with pytest.raises(cloudflare.CloudflarePublishingError) as error:
        cloudflare.run_command(
            arguments,
            tmp_path,
            {},
        )

    assert str(error.value) == "Wrangler failed: deployment rejected"


def test_publish_propagates_sanitized_publishing_error(
    tmp_path: pathlib.Path,
) -> None:
    def fail(
        arguments: tuple[str, ...],
        cwd: pathlib.Path,
        environ: dict[str, str],
    ) -> None:
        raise cloudflare.CloudflarePublishingError("Wrangler failed")

    with pytest.raises(cloudflare.CloudflarePublishingError) as error:
        cloudflare.publish(
            tmp_path / "site",
            tmp_path / "web",
            account_id="account-123",
            project="tech-sonar",
            secret="token-456",
            run=fail,
        )

    assert str(error.value) == "Wrangler failed"
    assert "token-456" not in str(error.value)
