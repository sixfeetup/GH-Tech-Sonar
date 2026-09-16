import datetime
import json
import pathlib

import pytest

from tech_sonar import generate
from tech_sonar import model


REPOSITORY = model.Repository("sixfeetup", "sonar")


def label(
    name: str,
    description: str | None = None,
) -> model.Label:
    return model.Label(
        name=name,
        color="ededed",
        description=description,
    )


def pull_request(
    number: int,
    state: str = "OPEN",
    merged: bool = False,
) -> model.PullRequest:
    return model.PullRequest(
        number=number,
        title=f"ADR {number}",
        url=f"https://github.com/sixfeetup/sonar/pull/{number}",
        state=state,
        merged=merged,
        repository=REPOSITORY,
    )


def issue(
    number: int,
    labels: tuple[model.Label, ...],
    pull_requests: tuple[model.PullRequest, ...] = (),
) -> model.Issue:
    return model.Issue(
        number=number,
        title=f"Issue {number}",
        url=f"https://github.com/sixfeetup/sonar/issues/{number}",
        state="OPEN",
        updated_at="2026-09-15T18:00:00Z",
        body_html=f"<p>Issue {number}</p>",
        labels=labels,
        pull_requests=pull_requests,
    )


def test_build_snapshot_selects_and_derives_items() -> None:
    issues = (
        issue(2, labels=(label("documentation"),)),
        issue(
            1,
            labels=(
                label("SONAR PROPOSE"),
                label("SONAR EXPLORE"),
                label("SONAR CATEGORY Languages"),
                label("SONAR CATEGORY Platforms"),
            ),
            pull_requests=(pull_request(20, state="OPEN", merged=False),),
        ),
    )

    snapshot = generate.build_snapshot(
        REPOSITORY,
        issues,
        "2026-09-15T20:30:00Z",
    )

    assert [item.number for item in snapshot.items] == [1]
    assert snapshot.items[0].statuses == (
        model.Status.EXPLORE,
        model.Status.PROPOSE,
    )
    assert snapshot.items[0].categories == ("Languages", "Platforms")
    assert snapshot.items[0].warnings == ()


def test_build_snapshot_uses_uncategorised_without_category() -> None:
    snapshot = generate.build_snapshot(
        REPOSITORY,
        (issue(1, labels=(label("SONAR EXPLORE"),)),),
        "2026-09-15T20:30:00Z",
    )

    assert snapshot.items[0].categories == ("Uncategorised",)


def test_build_snapshot_warns_for_propose_without_open_pr() -> None:
    snapshot = generate.build_snapshot(
        REPOSITORY,
        (issue(1, labels=(label("SONAR PROPOSE"),)),),
        "2026-09-15T20:30:00Z",
    )

    assert len(snapshot.items[0].warnings) == 1
    warning = snapshot.items[0].warnings[0]
    assert warning.code == "missing-propose-evidence"
    assert warning.status is model.Status.PROPOSE
    assert "issue 1" in warning.message.lower()
    assert "PROPOSE" in warning.message
    assert "open pull request" in warning.message


def test_build_snapshot_warns_for_adopt_without_merged_pr() -> None:
    snapshot = generate.build_snapshot(
        REPOSITORY,
        (
            issue(
                1,
                labels=(label("SONAR ADOPT"),),
                pull_requests=(pull_request(10),),
            ),
        ),
        "2026-09-15T20:30:00Z",
    )

    assert len(snapshot.items[0].warnings) == 1
    warning = snapshot.items[0].warnings[0]
    assert warning.code == "missing-adopt-evidence"
    assert warning.status is model.Status.ADOPT
    assert "issue 1" in warning.message.lower()
    assert "ADOPT" in warning.message
    assert "merged pull request" in warning.message


def test_build_snapshot_accepts_merged_pr_as_adopt_evidence() -> None:
    snapshot = generate.build_snapshot(
        REPOSITORY,
        (
            issue(
                1,
                labels=(label("SONAR ADOPT"),),
                pull_requests=(
                    pull_request(10, state="CLOSED", merged=True),
                ),
            ),
        ),
        "2026-09-15T20:30:00Z",
    )

    assert snapshot.items[0].warnings == ()


def test_closed_unmerged_pr_satisfies_neither_evidence_rule() -> None:
    snapshot = generate.build_snapshot(
        REPOSITORY,
        (
            issue(
                1,
                labels=(
                    label("SONAR PROPOSE"),
                    label("SONAR ADOPT"),
                ),
                pull_requests=(
                    pull_request(10, state="CLOSED", merged=False),
                ),
            ),
        ),
        "2026-09-15T20:30:00Z",
    )

    assert [warning.code for warning in snapshot.items[0].warnings] == [
        "missing-propose-evidence",
        "missing-adopt-evidence",
    ]


def test_build_snapshot_stably_orders_items_and_nested_values() -> None:
    issues = (
        issue(
            2,
            labels=(
                label("zeta"),
                label("SONAR CATEGORY Platforms"),
                label("SONAR PROPOSE"),
                label("SONAR CATEGORY Languages"),
                label("SONAR REJECT"),
                label("alpha"),
            ),
            pull_requests=(pull_request(20), pull_request(10)),
        ),
        issue(1, labels=(label("SONAR HOLD"),)),
    )

    snapshot = generate.build_snapshot(
        REPOSITORY,
        issues,
        "2026-09-15T20:30:00Z",
    )

    assert [item.number for item in snapshot.items] == [1, 2]
    item = snapshot.items[1]
    assert [value.name for value in item.labels] == sorted(
        value.name for value in item.labels
    )
    assert item.statuses == (
        model.Status.REJECT,
        model.Status.PROPOSE,
    )
    assert item.categories == ("Languages", "Platforms")
    assert [value.number for value in item.pull_requests] == [10, 20]


def test_write_snapshot_uses_the_static_json_contract(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_directory = tmp_path / "artifact"
    output_directory.mkdir()
    monkeypatch.setattr(
        "tempfile.mkdtemp",
        lambda prefix: str(output_directory),
    )
    snapshot = generate.build_snapshot(
        REPOSITORY,
        (
            issue(
                1,
                labels=(
                    label("SONAR PROPOSE", description=None),
                    label("SONAR CATEGORY Languages"),
                ),
                pull_requests=(
                    pull_request(10, state="CLOSED", merged=False),
                ),
            ),
        ),
        "2026-09-15T20:30:00Z",
    )

    path = generate.write_snapshot(snapshot)

    assert path.is_absolute()
    assert path.name == "sonar.json"
    data = json.loads(path.read_text())
    assert list(data) == ["repository", "generatedAt", "items"]
    assert data["generatedAt"] == "2026-09-15T20:30:00Z"
    item_data = data["items"][0]
    assert list(item_data) == [
        "number",
        "title",
        "url",
        "state",
        "updatedAt",
        "bodyHtml",
        "labels",
        "statuses",
        "categories",
        "pullRequests",
        "warnings",
    ]
    assert item_data["updatedAt"] == "2026-09-15T18:00:00Z"
    assert item_data["bodyHtml"] == "<p>Issue 1</p>"
    assert item_data["labels"][1]["description"] is None
    assert item_data["pullRequests"] == [
        {
            "number": 10,
            "title": "ADR 10",
            "url": "https://github.com/sixfeetup/sonar/pull/10",
            "state": "CLOSED",
            "merged": False,
        },
    ]
    assert set(item_data["warnings"][0]) == {"code", "message", "status"}
    assert item_data["warnings"][0]["status"] == "PROPOSE"
    text = path.read_text()
    assert '\n  "generatedAt"' in text
    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_write_snapshot_is_deterministic(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directories = [tmp_path / "first", tmp_path / "second"]
    for directory in directories:
        directory.mkdir()
    directory_names = iter(str(directory) for directory in directories)
    monkeypatch.setattr(
        "tempfile.mkdtemp",
        lambda prefix: next(directory_names),
    )
    snapshot = generate.build_snapshot(
        REPOSITORY,
        (issue(1, labels=(label("SONAR EXPLORE"),)),),
        "2026-09-15T20:30:00Z",
    )

    first = generate.write_snapshot(snapshot)
    second = generate.write_snapshot(snapshot)

    assert first.read_bytes() == second.read_bytes()


def test_utc_timestamp_returns_rfc3339_utc_value() -> None:
    timestamp = generate.utc_timestamp()

    assert timestamp.endswith("Z")
    parsed = datetime.datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
    assert parsed.tzinfo is datetime.UTC
