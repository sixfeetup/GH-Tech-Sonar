import subprocess

import pytest

from tech_sonar import auth


def test_resolve_token_prefers_environment() -> None:
    def unexpected_fallback() -> str:
        raise AssertionError("fallback must not run")

    token = auth.resolve_token(
        {"GH_TOKEN": "action-token"},
        unexpected_fallback,
    )

    assert token == "action-token"


def test_resolve_token_uses_gh_fallback() -> None:
    token = auth.resolve_token({}, lambda: "local-token")

    assert token == "local-token"


def test_resolve_token_rejects_empty_sources() -> None:
    with pytest.raises(auth.AuthenticationError, match="GH_TOKEN"):
        auth.resolve_token({}, lambda: "")


def test_gh_auth_token_reports_command_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, ["gh", "auth", "token"])

    monkeypatch.setattr(subprocess, "run", fail)

    with pytest.raises(auth.AuthenticationError, match="gh auth login"):
        auth.gh_auth_token()
