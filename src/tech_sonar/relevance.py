import collections.abc
import re

from tech_sonar import generate
from tech_sonar import model


_REFERENCE = re.compile(r"(?:^|[\s([{,:;])#([1-9]\d*)\b")
_STATUS_LABELS = frozenset(generate.STATUS_LABELS)
_ERROR_PREFIX = "malformed GitHub pull-request event"


class RelevanceError(ValueError):
    pass


def _malformed(detail: str) -> RelevanceError:
    return RelevanceError(f"{_ERROR_PREFIX}: {detail}")


def _event_repository(event: object) -> model.Repository:
    if not isinstance(event, dict):
        raise _malformed("payload must be an object")
    repository_data = event.get("repository")
    if not isinstance(repository_data, dict):
        raise _malformed("repository must be an object")
    full_name = repository_data.get("full_name")
    if not isinstance(full_name, str):
        raise _malformed("repository.full_name must be a string")
    try:
        return model.Repository.parse(full_name)
    except ValueError as error:
        raise _malformed("repository.full_name is invalid") from error


def _event_text(event: object) -> tuple[str, ...]:
    if not isinstance(event, dict):
        raise _malformed("payload must be an object")
    action = event.get("action")
    if not isinstance(action, str):
        raise _malformed("action must be a string")
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        raise _malformed("pull_request must be an object")

    title = pull_request.get("title")
    if not isinstance(title, str):
        raise _malformed("pull_request.title must be a string")
    body = pull_request.get("body")
    if body is not None and not isinstance(body, str):
        raise _malformed("pull_request.body must be a string or null")

    text = [title]
    if body is not None:
        text.append(body)

    if action == "edited":
        changes = event.get("changes")
        if not isinstance(changes, dict):
            raise _malformed("changes must be an object")
        for field in ("title", "body"):
            if field not in changes:
                continue
            change = changes[field]
            if not isinstance(change, dict) or "from" not in change:
                raise _malformed(f"changes.{field}.from is invalid")
            previous = change["from"]
            if previous is not None and not isinstance(previous, str):
                raise _malformed(f"changes.{field}.from is invalid")
            if previous is not None:
                text.append(previous)

    return tuple(text)


def candidate_issue_numbers(event: object) -> tuple[int, ...]:
    _event_repository(event)
    numbers = [
        int(match.group(1))
        for text in _event_text(event)
        for match in _REFERENCE.finditer(text)
    ]
    return tuple(dict.fromkeys(numbers))


IssueLabelFetcher = collections.abc.Callable[
    [model.Repository, int],
    tuple[model.Label, ...] | None,
]


def pull_request_event_is_relevant(
    event: object,
    fetch_issue_labels: IssueLabelFetcher,
) -> bool:
    repository = _event_repository(event)
    for number in candidate_issue_numbers(event):
        labels = fetch_issue_labels(repository, number)
        if labels is not None and any(
            label.name in _STATUS_LABELS for label in labels
        ):
            return True
    return False
