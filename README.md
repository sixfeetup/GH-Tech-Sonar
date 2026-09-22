# Tech Sonar

Tech Sonar publishes an organization's technology decisions from GitHub issues
as a static snapshot.

## Web application

See the [web application guide](web/README.md) for frontend development, test,
and build commands.

## Prerequisites

Install `git`, `gh`, and `uv`. Authenticate the GitHub CLI before running Tech
Sonar locally:

```console
gh auth login
```

Git push credentials must also be configured. The authenticated user or token
needs these repository permissions:

- metadata: read;
- issues and labels: write;
- contents: write;
- pull requests: write.

## Install Tech Sonar

From a Tech Sonar source checkout, install its dependencies and install the
managed files in a target GitHub repository:

```console
# From a Tech Sonar source checkout
uv sync
uv run tech-sonar install OWNER/REPOSITORY
```

For installation and updates, the selected Tech Sonar source checkout must be
clean and have a committed `HEAD`.

Installation clones the target into `./REPOSITORY`, creates any missing status
labels, and proposes the managed workflow and Technology issue form on a new
branch and pull request. The issue form applies `SONAR EXPLORE` by default and
prompts authors to select manually maintained category labels in GitHub's label
sidebar.

Label changes take effect immediately and are not rolled back if a later step
fails. Existing labels are preserved, including their colors and descriptions.
Category labels are created and maintained manually.

## Configure publishing

Configure the target repository with the Cloudflare account and Pages project:

```console
gh variable set PUBLISH_ARGS \
  --repo OWNER/REPOSITORY \
  --body 'cloudflare ACCOUNT_ID PROJECT'
gh secret set PUBLISH_SECRET --repo OWNER/REPOSITORY
```

Enter the Cloudflare API token interactively when setting `PUBLISH_SECRET`. The
API token needs Account / Cloudflare Pages / Edit permission for the specified
account. `PUBLISH_ARGS` is parsed as shell-style arguments.

Before publishing, the operator must ensure that:

- the Pages project already exists;
- its production domain is configured;
- its Cloudflare Access application and policy already protect the site.

Every successful managed action currently publishes the site. Missing
publishing configuration fails the action. The assembled site is retained for
one day as the `tech-sonar-site` artifact for debugging, including after a
deployment failure.

Install and update do not create `PUBLISH_ARGS`, `PUBLISH_SECRET`, the Pages
project, its domain, or its Access application and policy.

## Update Tech Sonar

Run updates from the installed target repository checkout. Until Tech Sonar is
published, select the Tech Sonar source checkout with `--project`:

```console
# From an installed target repository checkout
uv run --project /path/to/GH-Tech-Sonar tech-sonar update
```

Updates create missing labels and compare the installed workflow and Technology
issue form with the canonical files from the running Tech Sonar revision.
Canonical content replaces both managed files through a branch and pull request.

On the default branch, an update creates a new installation branch. On a
non-default branch, it updates that branch and either updates its existing pull
request or opens one against the default branch. Install and update fail when
the target worktree is dirty. A no-op update creates no commit, push, or pull
request, though it may already have created missing labels.

## Generate a snapshot

Run generation from the installed target repository checkout:

```console
# From an installed target repository checkout
uv run --project /path/to/GH-Tech-Sonar tech-sonar generate
```

In GitHub Actions, provide the workflow token as `GH_TOKEN`:

```yaml
env:
  GH_TOKEN: ${{ github.token }}
```

On success, standard output contains only the absolute path to the generated
`sonar.json` artifact. Warnings and other diagnostics are written to standard
error, so callers can safely capture and consume the path. The caller owns the
temporary artifact directory and should remove it after use:

```bash
artifact=$(uv run tech-sonar generate)
consume-artifact "$artifact"
rm -rf "$(dirname "$artifact")"
```

See the [GitHub issue data model](docs/github-issue-data-model.md) for source
semantics and the generated JSON fields.

## Event filtering

The managed workflow skips non-Sonar issue events before allocating a runner.
It also skips PR pushes and edits unrelated to the PR title or body. PRs affect
Sonar ADR evidence only through local `#<digits>` references in their title or
body. Accepted PR events run targeted relevance detection before full snapshot
generation.
