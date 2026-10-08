# Technology reaction votes

## Goal and scope

Issue #28 lets Tech Sonar users express support or concern through 👍 and 👎
reactions on a technology's GitHub issue description. The app shows both counts
so readers can assess community sentiment.

Only reactions on the issue description count. Reactions on comments or pull
requests do not count. Other reaction types do not count. The existing Sonar
status-label rules still determine which open and closed issues appear.

GitHub remains the voting interface. This feature adds no voting controls,
voter identities, net score, ranking, or changes to placement and filtering.

## Proposed behavior

- Each 👍 reaction contributes one upvote. Each 👎 reaction contributes one
  downvote. The counts remain independent, including when one user adds both.
- Each generation reads the current totals, rather than accumulating votes
  across snapshots. Removing a reaction reduces its count in the next snapshot.
- An issue with no votes has zero upvotes and zero downvotes.
- Counts describe the source at collection time. They are not live browser data.
  The existing snapshot generation timestamp identifies snapshot freshness.
- Collection errors fail generation under the existing complete-snapshot policy.
  Missing or malformed source counts must not silently become zero.

The existing workflow has manual dispatch and issue/PR triggers, but no explicit
reaction trigger. This feature collects votes on the next generation. It does
not add a refresh schedule or promise immediate updates after a reaction.
Manual dispatch remains available to refresh the published snapshot.

## Data flow and contract

Use the existing GitHub client → issue model → snapshot generator → static web
application flow. Collect aggregate totals for the issue description rather
than storing individual reactions or voters. The later implementation plan
selects and verifies the GitHub API fields and collection method. This spec does
not prescribe a query or a new collection subsystem.

Add required `upvotes` and `downvotes` fields to each snapshot item, immediately
after `bodyHtml`:

```json
{
  "bodyHtml": "<p>Technology description</p>",
  "upvotes": 12,
  "downvotes": 4
}
```

This is an item excerpt, not a complete snapshot. Both counts are nonnegative
integers. The generator preserves the existing key order and deterministic
output rules for all other fields.

The frontend schema requires both fields. Missing fields are invalid, not zero
votes. Update the generator, frontend schema, and bundled fixtures together.
Regenerate snapshots before use with the new frontend. The current strict
schema also means that older frontends reject snapshots with the new fields.

## Display

Show a read-only Votes entry in list items and technology details, such as
`12 👍 / 4 👎`. Show both counts even when either count is zero. Provide an
accessible equivalent such as “12 upvotes, 4 downvotes” instead of relying on
emoji names alone.

Show the same summary in the visual Sonar's existing hover/focus tooltip.
Keep markers and layout unchanged. All placements of a technology use the same
item counts. The existing GitHub issue link remains the route to add or remove
reactions.

## Affected components

- `src/tech_sonar/github.py`: collect and validate the two source totals.
- `src/tech_sonar/model.py`: carry counts on `Issue` and `SonarItem`.
- `src/tech_sonar/generate.py`: preserve counts and serialize the new fields.
- `web/src/data/sonar.ts`: validate counts and expose them through inferred types.
- `web/src/list/ListView.tsx`, `web/src/details/ItemDetails.tsx`, and
  `web/src/sonar/SonarView.tsx`: show a consistent, accessible vote summary.
- Backend and frontend fixtures, including `web/public/sonar.json`: supply counts.
- `docs/github-issue-data-model.md` and `docs/using-tech-sonar.md`: document the
  contract, voting location, and snapshot refresh behavior.

## Verification strategy

Automated tests must prove behavior at the source, snapshot, and display
boundaries:

- GitHub client tests verify independent totals, zero votes, ignored reaction
  types, and explicit errors for missing or malformed totals. Fixtures must
  distinguish issue-description reactions from comment reactions.
- Generation tests verify count preservation, Sonar inclusion rules, and
  deterministic serialization. Changed source totals must replace prior totals.
- Frontend schema tests accept zero and positive integer counts. They reject
  missing, negative, fractional, and nonnumeric counts.
- Component tests verify both counts and accessible wording in the list,
  details, and hover/focus tooltip, including zero counts.

Run the existing Python and frontend suites and the frontend build during
implementation. Use a focused browser check for desktop and mobile readability.
Verify the selected API against a technology issue with description reactions
before completing implementation. No new tests are needed for documentation
text or unchanged workflow configuration.

## Planning handoff

This spec is the design artifact for the current planning pull request.
Patchmill owns pull request review and the next plan-creation step. No product
code, implementation task todos, or additional manual approval gate belong to
this spec-creation step.
