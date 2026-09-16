import argparse
import collections.abc
import os
import pathlib
import sys

from tech_sonar import auth
from tech_sonar import config
from tech_sonar import generate
from tech_sonar import github


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="tech-sonar")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("generate", help="generate a static Sonar snapshot")
    return result


def generate_command() -> int:
    settings = config.load_config(pathlib.Path("sonar.toml"))
    token = auth.resolve_token(os.environ)
    with github.GitHubClient(token) as client:
        issues = client.fetch_issues(settings.repository)
    snapshot = generate.build_snapshot(
        settings.repository,
        issues,
        generate.utc_timestamp(),
    )
    artifact = generate.write_snapshot(snapshot)
    for item in snapshot.items:
        for warning in item.warnings:
            print(
                f"warning: issue {item.number} [{warning.status.value}]: "
                f"{warning.message}",
                file=sys.stderr,
            )
    print(artifact)
    return 0


def main(argv: collections.abc.Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.command == "generate":
        try:
            return generate_command()
        except (
            config.ConfigError,
            auth.AuthenticationError,
            github.GitHubError,
            OSError,
        ) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    raise AssertionError(f"unexpected command: {arguments.command}")
