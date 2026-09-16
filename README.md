# Tech Sonar

Tech Sonar publishes an organization's technology decisions from GitHub
issues as static content.

## Generate a snapshot

Install the project dependencies and command:

```console
uv sync
```

Create `sonar.toml` in the directory where you will run the command:

```toml
repository = "sixfeetup/GH-Tech-Sonar"
```

In GitHub Actions, provide the workflow token as `GH_TOKEN`, for example:

```yaml
env:
  GH_TOKEN: ${{ github.token }}
```

For local use without `GH_TOKEN`, authenticate the GitHub CLI first:

```console
gh auth login
```

Generate the snapshot:

```console
uv run tech-sonar generate
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
