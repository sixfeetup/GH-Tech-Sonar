# Tech Sonar

The Tech Sonar provides a high-level view of technology adoption in an organization.

It's inspired by the Thoughworks Tech Radar: https://www.thoughtworks.com/en-us/radar.

There is an initial prototype here: https://sonar.demosnotmemos.com/

This implementation uses a github repository as a source of truth.

Github actions execute code that updates a static representation.

A dynamic React application provides an interactive view of the static
data.  This static website can be depoyed to any static web hosting
service.

## High-level design

Major components:

- Management of static content, implemented as a Python script with a
  CLI API.
- Content rendering via a TypeScript React application.
- Deployment script(s) to deploy application to static hosting service.
- Authenticated access to the static website.
- Workflow implemented via github actions that update static content
  and deploy to static web-hosting services.
- Python script to install against a repo
  - Labels
  - Actions
  - Optionally repo creation
- Automated tests

Basic organization:

- Source content is githhub issues with labels:

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

    SONAR ADOPT issues must have a PR link to an merged
    PR against the source repository.

  - Category labels.

    These labels must have names starting with "SONAR CATEGORY " but
    are otherwise unrestricted. They're displayed as slices, without
    the the "SONAR CATEGORY " prefix, according to the number of
    issues.  There's a default "Uncategorised" category.

## Guiding (but not-necessarily disqualifying) requirements:

- Easy to add new technologies being explored without much ceremony
  and without prior approval!!!
- Technology should be “adopted” through the ADR process.
- Easy to explore new tech and assess applicability to projects.
- Status meaning must be unambiguous
- Metadata describes what it applies to (e.g., new projects, existing
  projects, optional)
- Metadata describes if migration is expected (e.g., yes, no,
  case-by-case)
- Items should have a history of status change, person who changed,
  and why
- Distinguish org-wide decisions from project-specific architectural
  decisions.

## Questions:
- Do static hosting services provide authenticated access?  What about
  cloudflare pages?
- Do github issues provide history?

## Additional requirements

- Python code should use type anntations.

  - Types should represent domain concepts to the degree practical.

  - Type aliases should be used when implementing concepts with basic
    types (e.f. `str`, `tuple[str]`

- Typescript code should also use types/type-aliases to represent
  domain concept consistent with Python code.
