import dataclasses
import enum


class Status(enum.StrEnum):
    REJECT = "REJECT"
    HOLD = "HOLD"
    EXPLORE = "EXPLORE"
    PROPOSE = "PROPOSE"
    ADOPT = "ADOPT"


@dataclasses.dataclass(frozen=True, slots=True)
class Repository:
    owner: str
    name: str

    @classmethod
    def parse(cls, value: str) -> "Repository":
        parts = value.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("repository must use OWNER/REPOSITORY form")
        return cls(*parts)

    def __str__(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclasses.dataclass(frozen=True, slots=True)
class Label:
    name: str
    color: str
    description: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class PullRequest:
    number: int
    title: str
    url: str
    state: str
    merged: bool
    repository: Repository


@dataclasses.dataclass(frozen=True, slots=True)
class Issue:
    number: int
    title: str
    url: str
    state: str
    updated_at: str
    body_html: str
    labels: tuple[Label, ...]
    pull_requests: tuple[PullRequest, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class Warning:
    code: str
    message: str
    status: Status


@dataclasses.dataclass(frozen=True, slots=True)
class SonarItem:
    number: int
    title: str
    url: str
    state: str
    updated_at: str
    body_html: str
    labels: tuple[Label, ...]
    statuses: tuple[Status, ...]
    categories: tuple[str, ...]
    pull_requests: tuple[PullRequest, ...]
    warnings: tuple[Warning, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class Snapshot:
    repository: Repository
    generated_at: str
    items: tuple[SonarItem, ...]
