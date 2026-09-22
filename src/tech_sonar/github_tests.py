import json

import httpx
import pytest

from tech_sonar import github
from tech_sonar import model


REPOSITORY = model.Repository("sixfeetup", "sonar")


def response(data: object) -> httpx.Response:
    return httpx.Response(200, json={"data": data})


def pull_request_node(
    number: int,
    repository: str = "sixfeetup/sonar",
) -> dict[str, object]:
    return {
        "source": {
            "__typename": "PullRequest",
            "number": number,
            "title": f"ADR {number}",
            "url": f"https://github.com/{repository}/pull/{number}",
            "state": "OPEN",
            "merged": False,
            "repository": {"nameWithOwner": repository},
        },
    }


def issue_node(number: int) -> dict[str, object]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "url": f"https://github.com/sixfeetup/sonar/issues/{number}",
        "state": "OPEN",
        "updatedAt": "2026-09-15T18:00:00Z",
        "bodyHTML": f"<p>Issue {number}</p>",
        "labels": {
            "nodes": [
                {
                    "name": "SONAR EXPLORE",
                    "color": "ededed",
                    "description": "Under evaluation",
                },
            ],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        },
        "timelineItems": {
            "nodes": [pull_request_node(number + 100)],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        },
    }


def issue_response(node: dict[str, object]) -> httpx.Response:
    return response(
        {
            "repository": {
                "issues": {
                    "nodes": [node],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                },
            },
        },
    )


def issue_labels_data(
    labels: list[dict[str, object]],
    *,
    has_next: bool = False,
    cursor: str | None = None,
) -> dict[str, object]:
    return {
        "repository": {
            "issue": {
                "labels": {
                    "nodes": labels,
                    "pageInfo": {
                        "hasNextPage": has_next,
                        "endCursor": cursor,
                    },
                },
            },
        },
    }


def test_fetch_issue_labels_returns_labels() -> None:
    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(
            lambda request: response(
                issue_labels_data(
                    [
                        {
                            "name": "SONAR EXPLORE",
                            "color": "ededed",
                            "description": "Under evaluation",
                        },
                    ],
                ),
            ),
        ),
    )

    assert client.fetch_issue_labels(REPOSITORY, 17) == (
        model.Label(
            name="SONAR EXPLORE",
            color="ededed",
            description="Under evaluation",
        ),
    )


def test_fetch_issue_labels_returns_none_for_missing_issue() -> None:
    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "data": {"repository": {"issue": None}},
                    "errors": [
                        {
                            "type": "NOT_FOUND",
                            "path": ["repository", "issue"],
                            "locations": [{"line": 8, "column": 5}],
                            "message": (
                                "Could not resolve to an Issue with the number "
                                "of 17."
                            ),
                        },
                    ],
                },
            ),
        ),
    )

    assert client.fetch_issue_labels(REPOSITORY, 17) is None


def test_fetch_issue_labels_propagates_other_graphql_errors() -> None:
    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "data": {"repository": {"issue": None}},
                    "errors": [
                        {
                            "type": "FORBIDDEN",
                            "path": ["repository", "issue"],
                            "locations": [{"line": 8, "column": 5}],
                            "message": "Resource not accessible",
                        },
                    ],
                },
            ),
        ),
    )

    with pytest.raises(github.GitHubError, match="Resource not accessible"):
        client.fetch_issue_labels(REPOSITORY, 17)


def test_fetch_issue_labels_rejects_malformed_label_name() -> None:
    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(
            lambda request: response(
                issue_labels_data(
                    [
                        {
                            "name": None,
                            "color": "ededed",
                            "description": "Under evaluation",
                        },
                    ],
                ),
            ),
        ),
    )

    with pytest.raises(
        github.GitHubError,
        match="GitHub returned an incomplete or malformed response",
    ):
        client.fetch_issue_labels(REPOSITORY, 17)


def test_fetch_issue_labels_paginates_labels() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        variables = payload["variables"]
        if variables["after"] is None:
            return response(
                issue_labels_data(
                    [
                        {
                            "name": "documentation",
                            "color": "0075ca",
                            "description": None,
                        },
                    ],
                    has_next=True,
                    cursor="label-page-2",
                ),
            )
        assert variables == {
            "owner": "sixfeetup",
            "name": "sonar",
            "number": 17,
            "after": "label-page-2",
        }
        return response(
            issue_labels_data(
                [
                    {
                        "name": "SONAR EXPLORE",
                        "color": "ededed",
                        "description": "Under evaluation",
                    },
                ],
            ),
        )

    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(handler),
    )

    labels = client.fetch_issue_labels(REPOSITORY, 17)

    assert len(requests) == 2
    assert [label.name for label in labels or ()] == [
        "documentation",
        "SONAR EXPLORE",
    ]


def test_fetch_issues_paginates_collection() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        variables = payload["variables"]
        number = 1 if variables["after"] is None else 2
        has_next = variables["after"] is None
        cursor = "issue-page-2" if has_next else None
        return response(
            {
                "repository": {
                    "issues": {
                        "nodes": [issue_node(number)],
                        "pageInfo": {
                            "hasNextPage": has_next,
                            "endCursor": cursor,
                        },
                    },
                },
            },
        )

    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(handler),
    )

    issues = client.fetch_issues(REPOSITORY)

    assert [issue.number for issue in issues] == [1, 2]
    assert len(requests) == 2
    assert issues[0].body_html == "<p>Issue 1</p>"
    assert issues[0].labels == (
        model.Label(
            name="SONAR EXPLORE",
            color="ededed",
            description="Under evaluation",
        ),
    )
    assert issues[0].pull_requests == (
        model.PullRequest(
            number=101,
            title="ADR 101",
            url="https://github.com/sixfeetup/sonar/pull/101",
            state="OPEN",
            merged=False,
            repository=REPOSITORY,
        ),
    )


def test_fetch_issues_paginates_labels() -> None:
    node = issue_node(1)
    labels = node["labels"]
    assert isinstance(labels, dict)
    labels["pageInfo"] = {
        "hasNextPage": True,
        "endCursor": "label-page-2",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if "query Labels" not in payload["query"]:
            return issue_response(node)
        assert payload["variables"] == {
            "owner": "sixfeetup",
            "name": "sonar",
            "number": 1,
            "after": "label-page-2",
        }
        return response(
            {
                "repository": {
                    "issue": {
                        "labels": {
                            "nodes": [
                                {
                                    "name": "SONAR ADOPT",
                                    "color": "ffffff",
                                    "description": None,
                                },
                            ],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        },
                    },
                },
            },
        )

    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(handler),
    )

    issues = client.fetch_issues(REPOSITORY)

    assert [label.name for label in issues[0].labels] == [
        "SONAR ADOPT",
        "SONAR EXPLORE",
    ]


def test_fetch_issues_paginates_timeline_items() -> None:
    node = issue_node(1)
    timeline = node["timelineItems"]
    assert isinstance(timeline, dict)
    timeline["pageInfo"] = {
        "hasNextPage": True,
        "endCursor": "timeline-page-2",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if "query Timeline" not in payload["query"]:
            return issue_response(node)
        assert payload["variables"] == {
            "owner": "sixfeetup",
            "name": "sonar",
            "number": 1,
            "after": "timeline-page-2",
        }
        return response(
            {
                "repository": {
                    "issue": {
                        "timelineItems": {
                            "nodes": [pull_request_node(99)],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        },
                    },
                },
            },
        )

    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(handler),
    )

    issues = client.fetch_issues(REPOSITORY)

    assert [pull_request.number for pull_request in issues[0].pull_requests] == [
        99,
        101,
    ]


def test_fetch_issues_omits_pull_requests_from_other_repositories() -> None:
    node = issue_node(1)
    timeline = node["timelineItems"]
    assert isinstance(timeline, dict)
    timeline["nodes"] = [
        pull_request_node(101),
        pull_request_node(102, "sixfeetup/another-repository"),
    ]
    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(lambda request: issue_response(node)),
    )

    issues = client.fetch_issues(REPOSITORY)

    assert [pull_request.number for pull_request in issues[0].pull_requests] == [
        101,
    ]


def test_fetch_issues_includes_source_repository_with_canonical_casing() -> None:
    node = issue_node(1)
    timeline = node["timelineItems"]
    assert isinstance(timeline, dict)
    timeline["nodes"] = [pull_request_node(101, "SixFeetUp/Sonar")]
    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(lambda request: issue_response(node)),
    )

    issues = client.fetch_issues(REPOSITORY)

    assert [pull_request.number for pull_request in issues[0].pull_requests] == [
        101,
    ]


def test_fetch_issues_deduplicates_pull_requests() -> None:
    node = issue_node(1)
    timeline = node["timelineItems"]
    assert isinstance(timeline, dict)
    timeline["nodes"] = [pull_request_node(101), pull_request_node(101)]
    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(lambda request: issue_response(node)),
    )

    issues = client.fetch_issues(REPOSITORY)

    assert [pull_request.number for pull_request in issues[0].pull_requests] == [
        101,
    ]


def test_fetch_issues_translates_http_errors() -> None:
    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(401, json={"message": "Bad credentials"}),
        ),
    )

    with pytest.raises(github.GitHubError, match="401"):
        client.fetch_issues(REPOSITORY)


def test_fetch_issues_translates_graphql_errors() -> None:
    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"errors": [{"message": "Repository not found"}]},
            ),
        ),
    )

    with pytest.raises(github.GitHubError, match="Repository not found"):
        client.fetch_issues(REPOSITORY)


def test_fetch_issues_rejects_missing_pagination_cursor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return response(
            {
                "repository": {
                    "issues": {
                        "nodes": [],
                        "pageInfo": {
                            "hasNextPage": True,
                            "endCursor": None,
                        },
                    },
                },
            },
        )

    client = github.GitHubClient(
        "token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(github.GitHubError, match="without an end cursor"):
        client.fetch_issues(REPOSITORY)
