from collections.abc import Iterable
import datetime
import json
import pathlib
import tempfile

from tech_sonar import model


STATUS_LABELS = {
    "SONAR REJECT": model.Status.REJECT,
    "SONAR HOLD": model.Status.HOLD,
    "SONAR EXPLORE": model.Status.EXPLORE,
    "SONAR PROPOSE": model.Status.PROPOSE,
    "SONAR ADOPT": model.Status.ADOPT,
}
CATEGORY_PREFIX = "SONAR CATEGORY "
UNCATEGORISED = "Uncategorised"


def build_snapshot(
    repository: model.Repository,
    issues: Iterable[model.Issue],
    generated_at: str,
) -> model.Snapshot:
    items = tuple(
        item
        for issue in sorted(issues, key=lambda value: value.number)
        if (item := _sonar_item(issue)) is not None
    )
    return model.Snapshot(
        repository=repository,
        generated_at=generated_at,
        items=items,
    )


def _sonar_item(issue: model.Issue) -> model.SonarItem | None:
    label_names = {label.name for label in issue.labels}
    statuses = tuple(
        status
        for name, status in STATUS_LABELS.items()
        if name in label_names
    )
    if not statuses:
        return None

    categories = tuple(
        sorted(
            label.name.removeprefix(CATEGORY_PREFIX)
            for label in issue.labels
            if label.name.startswith(CATEGORY_PREFIX)
        ),
    ) or (UNCATEGORISED,)
    pull_requests = tuple(
        sorted(issue.pull_requests, key=lambda value: value.number),
    )
    return model.SonarItem(
        number=issue.number,
        title=issue.title,
        url=issue.url,
        state=issue.state,
        updated_at=issue.updated_at,
        body_html=issue.body_html,
        labels=tuple(sorted(issue.labels, key=lambda value: value.name)),
        statuses=statuses,
        categories=categories,
        pull_requests=pull_requests,
        warnings=_warnings(issue.number, statuses, pull_requests),
    )


def _warnings(
    issue_number: int,
    statuses: tuple[model.Status, ...],
    pull_requests: tuple[model.PullRequest, ...],
) -> tuple[model.Warning, ...]:
    warnings: list[model.Warning] = []
    if model.Status.PROPOSE in statuses and not any(
        pull_request.state == "OPEN" for pull_request in pull_requests
    ):
        warnings.append(
            model.Warning(
                code="missing-propose-evidence",
                message=(
                    f"Issue {issue_number} has PROPOSE status but requires "
                    "an open pull request."
                ),
                status=model.Status.PROPOSE,
            ),
        )
    if model.Status.ADOPT in statuses and not any(
        pull_request.merged for pull_request in pull_requests
    ):
        warnings.append(
            model.Warning(
                code="missing-adopt-evidence",
                message=(
                    f"Issue {issue_number} has ADOPT status but requires "
                    "a merged pull request."
                ),
                status=model.Status.ADOPT,
            ),
        )
    return tuple(warnings)


def snapshot_data(snapshot: model.Snapshot) -> dict[str, object]:
    return {
        "repository": str(snapshot.repository),
        "generatedAt": snapshot.generated_at,
        "items": [item_data(item) for item in snapshot.items],
    }


def item_data(item: model.SonarItem) -> dict[str, object]:
    return {
        "number": item.number,
        "title": item.title,
        "url": item.url,
        "state": item.state,
        "updatedAt": item.updated_at,
        "bodyHtml": item.body_html,
        "labels": [_label_data(label) for label in item.labels],
        "statuses": [status.value for status in item.statuses],
        "categories": list(item.categories),
        "pullRequests": [
            _pull_request_data(pull_request)
            for pull_request in item.pull_requests
        ],
        "warnings": [_warning_data(warning) for warning in item.warnings],
    }


def _label_data(label: model.Label) -> dict[str, object]:
    return {
        "name": label.name,
        "color": label.color,
        "description": label.description,
    }


def _pull_request_data(
    pull_request: model.PullRequest,
) -> dict[str, object]:
    return {
        "number": pull_request.number,
        "title": pull_request.title,
        "url": pull_request.url,
        "state": pull_request.state,
        "merged": pull_request.merged,
    }


def _warning_data(warning: model.Warning) -> dict[str, object]:
    return {
        "code": warning.code,
        "message": warning.message,
        "status": warning.status.value,
    }


def write_snapshot(snapshot: model.Snapshot) -> pathlib.Path:
    directory = pathlib.Path(
        tempfile.mkdtemp(prefix="tech-sonar-"),
    ).resolve()
    path = directory / "sonar.json"
    path.write_text(
        json.dumps(snapshot_data(snapshot), indent=2) + "\n",
    )
    return path


def utc_timestamp() -> str:
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    return timestamp.removesuffix("+00:00") + "Z"
