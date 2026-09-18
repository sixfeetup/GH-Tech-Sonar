import collections.abc
import importlib.resources
import os
import pathlib
import shlex
import shutil
import subprocess
import tempfile

from tech_sonar import cloudflare


BuildRunner = collections.abc.Callable[
    [tuple[str, ...], pathlib.Path],
    None,
]
CloudflarePublisher = collections.abc.Callable[
    [pathlib.Path, pathlib.Path, str, str, str],
    None,
]


class PublishingError(RuntimeError):
    pass


def parse_publisher_args(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()

    try:
        return tuple(shlex.split(value))
    except ValueError as error:
        raise PublishingError(f"invalid PUBLISH_ARGS: {error}") from error


def run_command(arguments: tuple[str, ...], cwd: pathlib.Path) -> None:
    child_environment = dict(os.environ)
    child_environment.pop("PUBLISH_SECRET", None)
    try:
        subprocess.run(
            arguments,
            cwd=cwd,
            env=child_environment,
            check=True,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise PublishingError(f"npm failed: {error}") from error
    except subprocess.CalledProcessError as error:
        raise PublishingError(
            f"npm failed: {error.stderr.strip()}",
        ) from error


def _filesystem_error(
    error: OSError,
    fallback_path: pathlib.Path,
) -> PublishingError:
    path = error.filename or fallback_path
    message = error.strerror or str(error)
    return PublishingError(f"filesystem operation failed for {path}: {message}")


def _publish(
    snapshot: pathlib.Path,
    output: pathlib.Path,
    publisher_args: tuple[str, ...],
    secret: str | None,
    web_source: pathlib.Path,
    run: BuildRunner,
    deploy: CloudflarePublisher,
) -> None:
    if output.exists():
        raise PublishingError(f"output directory already exists: {output}")
    if not secret:
        raise PublishingError("PUBLISH_SECRET is required")
    if not publisher_args:
        raise PublishingError("PUBLISH_ARGS is required")
    if publisher_args[0] != "cloudflare":
        raise PublishingError(
            f"unsupported publisher: {publisher_args[0]}",
        )
    if len(publisher_args) != 3:
        raise PublishingError(
            "cloudflare requires an account ID and project",
        )

    try:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = pathlib.Path(temporary_directory) / "web"
            shutil.copytree(web_source, workspace)
            shutil.copyfile(snapshot, workspace / "public" / "sonar.json")
            run(("npm", "ci"), workspace)
            run(("npm", "run", "build"), workspace)
            shutil.copytree(workspace / "dist", output)
            deploy(
                output,
                workspace,
                publisher_args[1],
                publisher_args[2],
                secret,
            )
    except OSError as error:
        raise _filesystem_error(error, output) from error


def publish(
    snapshot: pathlib.Path,
    output: pathlib.Path,
    publisher_args: tuple[str, ...],
    secret: str | None,
    web_source: pathlib.Path | None = None,
    run: BuildRunner = run_command,
    deploy: CloudflarePublisher = cloudflare.publish,
) -> None:
    if web_source is not None:
        _publish(
            snapshot,
            output,
            publisher_args,
            secret,
            web_source,
            run,
            deploy,
        )
        return

    resource = importlib.resources.files("tech_sonar").joinpath("web")
    with importlib.resources.as_file(resource) as packaged_web_source:
        _publish(
            snapshot,
            output,
            publisher_args,
            secret,
            packaged_web_source,
            run,
            deploy,
        )
