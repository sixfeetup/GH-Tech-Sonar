# Tech Sonar

Tech Sonar publishes an organization's technology decisions from GitHub issues
as a static snapshot.

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
labels, and proposes the managed workflow on a new branch and pull request.
Label changes take effect immediately and are not rolled back if a later step
fails. Existing labels are preserved, including their colors and descriptions.
Category labels are created and maintained manually.

## Update Tech Sonar

Run updates from the installed target repository checkout. Until Tech Sonar is
published, select the Tech Sonar source checkout with `--project`:

```console
# From an installed target repository checkout
uv run --project /path/to/GH-Tech-Sonar tech-sonar update
```

Updates create missing labels and compare the installed workflow with the
canonical workflow from the running Tech Sonar revision. The canonical content
overwrites `.github/workflows/tech-sonar.yml`; the change is made through a
branch and pull request.

On the default branch, an update creates a new installation branch. On a
non-default branch, it updates that branch and either updates its existing pull
request or opens one against the default branch. Install and update fail when
the target worktree is dirty. A no-op update creates no commit, push, or pull
request, though it may already have created missing labels.

The initial workflow generates a snapshot but does not deploy it.

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
