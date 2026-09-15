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

Missing ADR evidence creates a displayed warning for the affected item and does
not stop generation.

## Categories and placement

Category labels start with `SONAR CATEGORY `. The display category removes that
prefix. Issues without a category label use `Uncategorised`.

Issues with multiple status or category labels are placed in every corresponding
status band and category slice.

## Filtering

The application supports filtering by category and by GitHub issue `updatedAt`
modification time.

## Static contract

The static model stores each issue once. Each item contains:

- GitHub identity: number, title, URL, state, and `updatedAt`.
- Rendered body HTML.
- All labels, including name, color, and description.
- Derived statuses and categories.
- Cross-referencing pull-request summaries, including number, title, URL, state,
  and merged status.
- Structured warnings suitable for display.

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
