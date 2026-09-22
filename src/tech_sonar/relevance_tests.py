import pytest

from tech_sonar import github
from tech_sonar import model
from tech_sonar import relevance


def event(
    *,
    action: str = "opened",
    title: str = "Adopt it for #12",
    body: str | None = "Supports #34",
    changes: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "action": action,
        "repository": {"full_name": "sixfeetup/sonar"},
        "pull_request": {"title": title, "body": body},
        "changes": changes or {},
    }


def test_candidate_issue_numbers_include_current_and_previous_text() -> None:
    payload = event(
        action="edited",
        title="Adopt #12 and #12",
        body="See team/other#99 and #34",
        changes={
            "title": {"from": "Old #56"},
            "body": {"from": None},
        },
    )

    assert relevance.candidate_issue_numbers(payload) == (12, 34, 56)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {
            "action": "opened",
            "repository": {},
            "pull_request": {"title": "Adopt #12", "body": None},
            "changes": {},
        },
        {
            "action": "opened",
            "repository": {"full_name": "sixfeetup/sonar"},
            "changes": {},
        },
        {
            "action": "opened",
            "repository": {"full_name": "sixfeetup/sonar"},
            "pull_request": {"title": 12, "body": None},
            "changes": {},
        },
        {
            "action": "opened",
            "repository": {"full_name": "sixfeetup/sonar"},
            "pull_request": {"title": "Adopt #12", "body": 34},
            "changes": {},
        },
        {
            "action": "edited",
            "repository": {"full_name": "sixfeetup/sonar"},
            "pull_request": {"title": "Adopt #12", "body": None},
            "changes": {"title": {"from": 56}},
        },
    ],
)
def test_malformed_payload_raises_relevance_error(payload: object) -> None:
    with pytest.raises(
        relevance.RelevanceError,
        match="^malformed GitHub pull-request event",
    ):
        relevance.candidate_issue_numbers(payload)


def label(name: str) -> model.Label:
    return model.Label(name=name, color="ededed", description=None)


def test_relevant_event_stops_after_first_sonar_issue() -> None:
    calls: list[tuple[model.Repository, int]] = []

    def fetch(
        repository: model.Repository,
        number: int,
    ) -> tuple[model.Label, ...] | None:
        calls.append((repository, number))
        return {
            12: None,
            34: (label("documentation"),),
            56: (label("SONAR EXPLORE"),),
            78: (label("SONAR ADOPT"),),
        }[number]

    payload = event(title="#12 #34 #56 #78", body=None)

    assert relevance.pull_request_event_is_relevant(payload, fetch)
    assert calls == [
        (model.Repository("sixfeetup", "sonar"), 12),
        (model.Repository("sixfeetup", "sonar"), 34),
        (model.Repository("sixfeetup", "sonar"), 56),
    ]


def test_event_without_references_is_not_relevant() -> None:
    calls: list[int] = []

    def fetch(
        repository: model.Repository,
        number: int,
    ) -> tuple[model.Label, ...] | None:
        calls.append(number)
        return (label("SONAR ADOPT"),)

    assert not relevance.pull_request_event_is_relevant(
        event(title="No issue reference", body=None),
        fetch,
    )
    assert calls == []


def test_event_with_only_missing_or_non_sonar_issues_is_not_relevant() -> None:
    calls: list[int] = []

    def fetch(
        repository: model.Repository,
        number: int,
    ) -> tuple[model.Label, ...] | None:
        calls.append(number)
        return None if number == 12 else (label("documentation"),)

    assert not relevance.pull_request_event_is_relevant(
        event(title="#12 #34", body=None),
        fetch,
    )
    assert calls == [12, 34]


def test_github_error_propagates() -> None:
    error = github.GitHubError("lookup failed")

    def fetch(
        repository: model.Repository,
        number: int,
    ) -> tuple[model.Label, ...] | None:
        raise error

    with pytest.raises(github.GitHubError) as caught:
        relevance.pull_request_event_is_relevant(
            event(title="#12", body=None),
            fetch,
        )

    assert caught.value is error
