import argparse
import collections.abc
import os
import pathlib
import sys

from tech_sonar import auth
from tech_sonar import generate
from tech_sonar import github
from tech_sonar import installation
from tech_sonar import model
from tech_sonar import repository


SOURCE_ROOT = pathlib.Path(__file__).resolve().parents[2]


def repository_argument(value: str) -> model.Repository:
    try:
        return model.Repository.parse(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="tech-sonar")
    commands = result.add_subparsers(dest="command", required=True)
    install = commands.add_parser(
        "install",
        help="install Tech Sonar in a repository",
    )
    install.add_argument("repository", type=repository_argument)
    commands.add_parser("update", help="update the Tech Sonar installation")
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
    try:
        if arguments.command == "install":
            pull_request = installation.install(
                arguments.repository,
                pathlib.Path.cwd(),
                SOURCE_ROOT,
            )
            print(pull_request)
            return 0
        if arguments.command == "update":
            pull_request = installation.update(
                pathlib.Path.cwd(),
                SOURCE_ROOT,
            )
            if pull_request is not None:
                print(pull_request)
            return 0
        if arguments.command == "generate":
            return generate_command()
        raise AssertionError(f"unexpected command: {arguments.command}")
    except (
        installation.InstallationError,
        repository.RepositoryError,
        auth.AuthenticationError,
        github.GitHubError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
