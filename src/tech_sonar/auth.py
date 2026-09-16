import collections.abc
import subprocess


TokenSource = collections.abc.Callable[[], str]


class AuthenticationError(RuntimeError):
    pass


def gh_auth_token() -> str:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise AuthenticationError(
            "set GH_TOKEN or authenticate locally with `gh auth login`",
        ) from error
    return result.stdout.strip()


def resolve_token(
    environ: collections.abc.Mapping[str, str],
    gh_auth: TokenSource = gh_auth_token,
) -> str:
    token = environ.get("GH_TOKEN", "").strip()
    if token:
        return token

    token = gh_auth().strip()
    if token:
        return token

    raise AuthenticationError(
        "set GH_TOKEN or authenticate locally with `gh auth login`",
    )
