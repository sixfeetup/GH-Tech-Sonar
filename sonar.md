# Tech Sonar

The Tech Sonar provides a high-level view of technology adoption in an organization.

It's inspired by the Thoughtworks Tech Radar: https://www.thoughtworks.com/en-us/radar.

There is an initial prototype here: https://sonar.demosnotmemos.com/

This implementation uses a GitHub repository as a source of truth.

GitHub Actions execute code that updates a static representation.

A dynamic React application provides an interactive view of the static
data.  This static website can be deployed to any static web hosting
service.

## High-level design

Major components:

- Management of static content, implemented as a Python script with a
  CLI API.
- Content rendering via a TypeScript React application.
- Deployment script(s) to deploy application to static hosting service.
- Authenticated access to the static website.
- Workflow implemented via GitHub Actions that update static content
  and deploy to static web-hosting services.
- Python script to install against a repo
  - Labels
  - Actions
  - Optionally repo creation
- Automated tests

Basic organization:

- Source content is GitHub issues with labels. See
  [GitHub Issue Data Model](docs/github-issue-data-model.md) for source
  semantics and the static contract. Labels include:

  - Status labels:

    - SONAR REJECT
    - SONAR HOLD
    - SONAR EXPLORE
    - SONAR PROPOSE
    - SONAR ADOPT

    These labels are used to form bands with SONAR REJECT outermost
    and SONAR ADOPT in the middle.  Bands have areas configurable as
    percentages, but of equal area by default.

    SONAR PROPOSE issues must have a PR link to an unmerged
    PR against the source repository.

    SONAR ADOPT issues must have a PR link to a merged
    PR against the source repository.

    Open and closed issues are included. Issues without a status label
    are ignored, so removing the status label removes an item from the
    Sonar.

  - Category labels.

    These labels must have names starting with "SONAR CATEGORY " but
    are otherwise unrestricted. They're displayed as slices, without
    the the "SONAR CATEGORY " prefix, according to the number of
    issues.  There's a default "Uncategorised" category.

## Guiding (but not-necessarily disqualifying) requirements:

1. Easy to add new technologies being explored without much ceremony
   and without prior approval!!!
2. Technology should be “adopted” through the ADR process.
3. Easy to explore new tech and assess applicability to projects.
4. Status meaning must be unambiguous
5. Metadata describes what it applies to (e.g., new projects, existing
   projects, optional)
6. Metadata describes if migration is expected (e.g., yes, no,
   case-by-case)
7. Items should have a history of status change, person who changed,
   and why
8. Distinguish org-wide decisions from project-specific architectural
   decisions.
9. Items can be filtered by issue modification time.
10. Items can be filtered by category.

Note that GitHub issues can support requirements: 1, 5, 6, 7 and 8.

GitHub pull requests provide the basis for 2.

Note however that although github issues and PRs implement most of the
requirements, how some of this information is exposed in the
application is an application concern.

## Questions:
- Do static hosting services provide authenticated access?  What about
  Cloudflare Pages?

## Additional requirements

- Python code should use type annotations.

  - Types should represent domain concepts to the degree practical.

  - Type aliases should be used when implementing concepts with basic
    types (e.g. `str`, `tuple[str]`).

- TypeScript code should also use types/type-aliases to represent
  domain concept consistent with Python code.

- CSS should be used to control presentation to the degree practical.
