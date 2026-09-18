import collections.abc
import os
import pathlib
import subprocess


CommandRunner = collections.abc.Callable[
    [tuple[str, ...], pathlib.Path, collections.abc.Mapping[str, str]],
    None,
]


class CloudflarePublishingError(RuntimeError):
    pass


def run_command(
    arguments: tuple[str, ...],
    cwd: pathlib.Path,
    environ: collections.abc.Mapping[str, str],
) -> None:
    try:
        subprocess.run(
            arguments,
            cwd=cwd,
            env=environ,
            check=True,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise CloudflarePublishingError(
            f"Wrangler failed: {error}",
        ) from error
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip()
        secret = environ.get("CLOUDFLARE_API_TOKEN")
        if secret:
            stderr = stderr.replace(secret, "[redacted]")
        raise CloudflarePublishingError(
            f"Wrangler failed: {stderr}",
        ) from error


def publish(
    site_directory: pathlib.Path,
    npm_root: pathlib.Path,
    account_id: str,
    project: str,
    secret: str,
    environ: collections.abc.Mapping[str, str] = os.environ,
    run: CommandRunner = run_command,
) -> None:
    child_environ = dict(environ)
    child_environ.pop("PUBLISH_SECRET", None)
    child_environ["CLOUDFLARE_ACCOUNT_ID"] = account_id
    child_environ["CLOUDFLARE_API_TOKEN"] = secret
    run(
        (
            "npm",
            "exec",
            "wrangler",
            "pages",
            "deploy",
            str(site_directory),
            "--project-name",
            project,
        ),
        npm_root,
        child_environ,
    )
