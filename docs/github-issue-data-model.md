# GitHub Issue Data Model

This document defines the GitHub source content consumed by the Tech Sonar
snapshot generator and the language-neutral static contract consumed by the
application.

## Included issues

The source repository includes open and closed issues that have one or more of
these status labels:

- `SONAR EXPLORE`
- `SONAR PROPOSE`
- `SONAR ADOPT`
- `SONAR HOLD`
- `SONAR REJECT`

Issues without any of these labels are excluded. Removing all status labels
removes the issue from the generated Sonar without deleting its GitHub history.

## Captured GitHub data

For every included issue, the generator captures:

- Number, title, URL, state, and `updatedAt`.
- GitHub-rendered `bodyHTML`.
- All labels, including name, color, and description.
- Source-repository pull requests that cross-reference the issue.
- Item warnings.

## Opaque issue content and history

The issue body is displayed as GitHub-rendered HTML. The generator does not
parse organization metadata such as applicability or migration guidance.

GitHub remains the source for timeline, actor, date, comments, and rationale.
The application links to the GitHub issue for that history instead of copying
it into the static data.

## Status semantics

- `EXPLORE`: Under evaluation without prior approval.
- `PROPOSE`: Recommended through an open ADR pull request.
- `ADOPT`: Approved through a merged ADR pull request.
- `HOLD`: Do not expand usage; existing usage may continue.
- `REJECT`: Do not use for new work; migration guidance belongs in the issue.

## ADR evidence

Any open pull request in the source repository that cross-references the issue
supports `PROPOSE`. Any merged pull request in the source repository that
cross-references the issue supports `ADOPT`. A closed, unmerged pull request
supports neither status.

Missing ADR evidence creates a displayed warning for the affected status
placement and does not stop generation.

## Categories and placement

Category labels start with `SONAR CATEGORY `. The display category removes that
prefix. Issues without a category label use `Uncategorised`.

Issues with multiple status or category labels are placed in every corresponding
status band and category slice.

## Filtering

The application supports filtering by category and by GitHub issue `updatedAt`
modification time.

## Static contract

The top-level document identifies the source repository, records when the
snapshot was generated, and contains the item collection:

```json
{
  "repository": "sixfeetup/GH-Tech-Sonar",
  "generatedAt": "2026-09-15T20:30:00Z",
  "items": []
}
```

`generatedAt` is the actual UTC time at which the generator creates the
snapshot. It is the only intentionally variable value when the source data is
unchanged.

The static model stores each issue once. An item has this shape:

```json
{
  "number": 3,
  "title": "Generate validated static Sonar content",
  "url": "https://github.com/sixfeetup/GH-Tech-Sonar/issues/3",
  "state": "OPEN",
  "updatedAt": "2026-09-15T18:00:00Z",
  "bodyHtml": "<p>...</p>",
  "labels": [
    {
      "name": "SONAR EXPLORE",
      "color": "ededed",
      "description": null
    }
  ],
  "statuses": ["EXPLORE"],
  "categories": ["Uncategorised"],
  "pullRequests": [],
  "warnings": []
}
```

A pull-request summary has this shape:

```json
{
  "number": 10,
  "title": "Approve the ADR",
  "url": "https://github.com/sixfeetup/GH-Tech-Sonar/pull/10",
  "state": "CLOSED",
  "merged": true
}
```

A warning has the keys `code`, `message`, and `status`, in that order:

```json
{
  "code": "missing-adopt-evidence",
  "message": "Issue 3 has ADOPT status but requires a merged pull request.",
  "status": "ADOPT"
}
```

Top-level and item keys remain in the order shown above. Items are ordered by
issue number; labels and categories by name; statuses by band order (`REJECT`,
`HOLD`, `EXPLORE`, `PROPOSE`, `ADOPT`); and pull requests by number. Warnings
follow the same status-band order. JSON uses two-space indentation and ends
with exactly one newline.

The UI derives repeated status-band and category-slice placements from each
item's status and category collections.

## Error behavior

Source-content inconsistencies, such as missing ADR evidence, become item
warnings. Failures that prevent a complete snapshot fail explicitly so an
incomplete snapshot is not published.

## GraphQL feasibility

The GitHub GraphQL API was verified for a single issue with these fields:
`number`, `title`, `url`, `state`, `updatedAt`, `bodyHTML`, labels with `name`,
`color`, and `description`, and `CROSS_REFERENCED_EVENT` timeline items whose
pull-request sources expose `number`, `title`, `url`, `state`, and `merged`.

The issue collection query was verified with `states: [OPEN, CLOSED]`, issue
`number` and `state`, and pagination through `pageInfo.hasNextPage` and
`pageInfo.endCursor`.
