import argparse
import collections.abc
import os
import pathlib
import sys

from tech_sonar import auth
from tech_sonar import generate
from tech_sonar import github
from tech_sonar import repository


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="tech-sonar")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("generate", help="generate a static Sonar snapshot")
    return result


def generate_command() -> int:
    target = repository.repository_at(pathlib.Path.cwd())
    token = auth.resolve_token(os.environ)
    with github.GitHubClient(token) as client:
        issues = client.fetch_issues(target)
    snapshot = generate.build_snapshot(
        target,
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
            repository.RepositoryError,
            auth.AuthenticationError,
            github.GitHubError,
            OSError,
        ) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    raise AssertionError(f"unexpected command: {arguments.command}")
