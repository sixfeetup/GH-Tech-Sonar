from typing import Any

import httpx

from tech_sonar import model


GRAPHQL_URL = "https://api.github.com/graphql"

ISSUES_QUERY = """
query Issues($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    issues(first: 100, after: $after, states: [OPEN, CLOSED]) {
      nodes {
        number title url state updatedAt bodyHTML
        labels(first: 100) {
          nodes { name color description }
          pageInfo { hasNextPage endCursor }
        }
        timelineItems(
          first: 100
          itemTypes: [CROSS_REFERENCED_EVENT]
        ) {
          nodes {
            ... on CrossReferencedEvent {
              source {
                __typename
                ... on PullRequest {
                  number title url state merged
                  repository { nameWithOwner }
                }
              }
            }
          }
          pageInfo { hasNextPage endCursor }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

LABELS_QUERY = """
query Labels(
  $owner: String!
  $name: String!
  $number: Int!
  $after: String
) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      labels(first: 100, after: $after) {
        nodes { name color description }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""

TIMELINE_QUERY = """
query Timeline(
  $owner: String!
  $name: String!
  $number: Int!
  $after: String
) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      timelineItems(
        first: 100
        after: $after
        itemTypes: [CROSS_REFERENCED_EVENT]
      ) {
        nodes {
          ... on CrossReferencedEvent {
            source {
              __typename
              ... on PullRequest {
                number title url state merged
                repository { nameWithOwner }
              }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""


class GitHubError(RuntimeError):
    pass


def _repository_key(repository: model.Repository) -> tuple[str, str]:
    return repository.owner.casefold(), repository.name.casefold()


class GitHubClient:
    def __init__(
        self,
        token: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=GRAPHQL_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "tech-sonar",
            },
            transport=transport,
            timeout=30,
        )

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        self._client.close()

    def fetch_issues(
        self,
        repository: model.Repository,
    ) -> tuple[model.Issue, ...]:
        try:
            return self._fetch_issues(repository)
        except (KeyError, TypeError, ValueError) as error:
            raise GitHubError(
                "GitHub returned an incomplete or malformed response",
            ) from error

    def fetch_issue_labels(
        self,
        repository: model.Repository,
        issue_number: int,
    ) -> tuple[model.Label, ...] | None:
        try:
            return self._fetch_issue_labels(repository, issue_number)
        except (KeyError, TypeError, ValueError) as error:
            raise GitHubError(
                "GitHub returned an incomplete or malformed response",
            ) from error

    def _fetch_issue_labels(
        self,
        repository: model.Repository,
        issue_number: int,
    ) -> tuple[model.Label, ...] | None:
        labels: list[model.Label] = []
        after: str | None = None
        while True:
            data = self._graphql(
                LABELS_QUERY,
                allow_missing_issue=True,
                owner=repository.owner,
                name=repository.name,
                number=issue_number,
                after=after,
            )
            issue = data["repository"]["issue"]
            if issue is None:
                if after is None:
                    return None
                raise TypeError("issue disappeared during label pagination")
            connection = issue["labels"]
            labels.extend(
                self._parse_label(node)
                for node in connection["nodes"]
            )
            page = connection["pageInfo"]
            if not page["hasNextPage"]:
                return tuple(labels)
            after = page["endCursor"]
            if not after:
                raise GitHubError(
                    "GitHub label pagination continued without an end cursor",
                )

    def _fetch_issues(
        self,
        repository: model.Repository,
    ) -> tuple[model.Issue, ...]:
        issues: list[model.Issue] = []
        after: str | None = None
        while True:
            data = self._graphql(
                ISSUES_QUERY,
                owner=repository.owner,
                name=repository.name,
                after=after,
            )
            connection = data["repository"]["issues"]
            issues.extend(
                self._parse_issue(repository, node)
                for node in connection["nodes"]
            )
            page = connection["pageInfo"]
            if not page["hasNextPage"]:
                return tuple(issues)
            after = page["endCursor"]
            if not after:
                raise GitHubError(
                    "GitHub issue pagination continued without an end cursor",
                )

    def _graphql(
        self,
        query: str,
        *,
        allow_missing_issue: bool = False,
        **variables: object,
    ) -> dict[str, Any]:
        repository = f"{variables.get('owner')}/{variables.get('name')}"
        try:
            response = self._client.post(
                GRAPHQL_URL,
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise GitHubError(
                f"GitHub request for {repository} failed: {error}",
            ) from error

        try:
            result = response.json()
            if not isinstance(result, dict):
                raise TypeError("GraphQL response is not an object")
            errors = result.get("errors")
            missing_issue = (
                allow_missing_issue
                and isinstance(errors, list)
                and len(errors) == 1
                and errors[0].get("type") == "NOT_FOUND"
                and errors[0].get("path") == ["repository", "issue"]
            )
            if errors and not missing_issue:
                message = errors[0]["message"]
                raise GitHubError(
                    f"GitHub GraphQL request for {repository} failed: {message}",
                )
            data = result["data"]
            if not isinstance(data, dict):
                raise TypeError("GraphQL data is not an object")
            return data
        except GitHubError:
            raise
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise GitHubError(
                "GitHub returned an incomplete or malformed response",
            ) from error

    def _parse_issue(
        self,
        repository: model.Repository,
        node: dict[str, Any],
    ) -> model.Issue:
        issue_number = node["number"]
        label_connection = node["labels"]
        labels = [
            self._parse_label(label)
            for label in label_connection["nodes"]
        ]
        label_page = label_connection["pageInfo"]
        if label_page["hasNextPage"]:
            label_cursor = label_page["endCursor"]
            if not label_cursor:
                raise GitHubError(
                    "GitHub label pagination continued without an end cursor",
                )
            labels.extend(
                self._remaining_labels(
                    repository,
                    issue_number,
                    label_cursor,
                ),
            )

        timeline_connection = node["timelineItems"]
        pull_requests = [
            pull_request
            for timeline_node in timeline_connection["nodes"]
            if (
                pull_request := self._parse_pull_request(timeline_node)
            ) is not None
        ]
        timeline_page = timeline_connection["pageInfo"]
        if timeline_page["hasNextPage"]:
            timeline_cursor = timeline_page["endCursor"]
            if not timeline_cursor:
                raise GitHubError(
                    "GitHub timeline pagination continued without an end cursor",
                )
            pull_requests.extend(
                self._remaining_pull_requests(
                    repository,
                    issue_number,
                    timeline_cursor,
                ),
            )

        repository_key = _repository_key(repository)
        unique_pull_requests = {
            pull_request.number: pull_request
            for pull_request in pull_requests
            if _repository_key(pull_request.repository) == repository_key
        }
        return model.Issue(
            number=issue_number,
            title=node["title"],
            url=node["url"],
            state=node["state"],
            updated_at=node["updatedAt"],
            body_html=node["bodyHTML"],
            labels=tuple(sorted(labels, key=lambda label: label.name)),
            pull_requests=tuple(
                unique_pull_requests[number]
                for number in sorted(unique_pull_requests)
            ),
        )

    def _remaining_labels(
        self,
        repository: model.Repository,
        issue_number: int,
        after: str,
    ) -> tuple[model.Label, ...]:
        labels: list[model.Label] = []
        cursor = after
        while True:
            data = self._graphql(
                LABELS_QUERY,
                owner=repository.owner,
                name=repository.name,
                number=issue_number,
                after=cursor,
            )
            connection = data["repository"]["issue"]["labels"]
            labels.extend(
                self._parse_label(node)
                for node in connection["nodes"]
            )
            page = connection["pageInfo"]
            if not page["hasNextPage"]:
                return tuple(labels)
            cursor = page["endCursor"]
            if not cursor:
                raise GitHubError(
                    "GitHub label pagination continued without an end cursor",
                )

    def _remaining_pull_requests(
        self,
        repository: model.Repository,
        issue_number: int,
        after: str,
    ) -> tuple[model.PullRequest, ...]:
        pull_requests: list[model.PullRequest] = []
        cursor = after
        while True:
            data = self._graphql(
                TIMELINE_QUERY,
                owner=repository.owner,
                name=repository.name,
                number=issue_number,
                after=cursor,
            )
            connection = data["repository"]["issue"]["timelineItems"]
            pull_requests.extend(
                pull_request
                for node in connection["nodes"]
                if (
                    pull_request := self._parse_pull_request(node)
                ) is not None
            )
            page = connection["pageInfo"]
            if not page["hasNextPage"]:
                return tuple(pull_requests)
            cursor = page["endCursor"]
            if not cursor:
                raise GitHubError(
                    "GitHub timeline pagination continued without an end cursor",
                )

    @staticmethod
    def _parse_label(node: dict[str, Any]) -> model.Label:
        name = node["name"]
        color = node["color"]
        description = node["description"]
        if not isinstance(name, str):
            raise TypeError("label name is not a string")
        if not isinstance(color, str):
            raise TypeError("label color is not a string")
        if description is not None and not isinstance(description, str):
            raise TypeError("label description is not a string or null")
        return model.Label(
            name=name,
            color=color,
            description=description,
        )

    @staticmethod
    def _parse_pull_request(
        node: dict[str, Any],
    ) -> model.PullRequest | None:
        source = node["source"]
        if source["__typename"] != "PullRequest":
            return None
        return model.PullRequest(
            number=source["number"],
            title=source["title"],
            url=source["url"],
            state=source["state"],
            merged=source["merged"],
            repository=model.Repository.parse(
                source["repository"]["nameWithOwner"],
            ),
        )
