# Using Tech Sonar

Tech Sonar helps you see which technologies your organization has approved,
is evaluating, has paused, or does not recommend. Each item comes from a GitHub
issue in the Sonar's source repository, so you can use GitHub to propose a
technology, record guidance, and discuss changes.

Technology can be software, hardware, or techniques.

## Browse the Sonar

Open your organization's Tech Sonar site. You can switch between two views:

- **Sonar** places technologies in status bands and category slices. `ADOPT` is
  at the center, followed by `PROPOSE`, `EXPLORE`, `HOLD`, and `REJECT`.
- **List** presents the same technologies as a list.

You can narrow either view by category, status, or the date an issue was last
updated. Select a technology to see its status, categories, description,
supporting pull requests, and any warnings. Follow **View issue and history on
GitHub** to read its discussion or make changes.

## Add a technology

1. Open the source repository's **Issues** page.
2. Choose **New issue**, then choose the **Technology** issue form.
3. Give the issue a title that names the technology.
4. Describe the technology, the projects it suits, and the skills needed to use
   and maintain it.
5. In the **Labels** sidebar, select one or more existing
   `SONAR CATEGORY …` labels. If none applies, leave the issue uncategorized.
6. Submit the issue.

The form assigns `SONAR EXPLORE` by default. After the publishing workflow
finishes successfully, the issue appears in the `EXPLORE` band.

## Share your experience with a technology

If you've used a technology, share your experience by commenting on a
technology issue.

## Manage a technology's status

Use one Sonar status label at a time. When the recommendation changes, remove
the previous status label and add the new one.

- **`SONAR EXPLORE`:** You are evaluating the technology without prior
  approval.
- **`SONAR PROPOSE`:** You recommend adoption through an open ADR pull request.
- **`SONAR ADOPT`:** An ADR pull request approving the technology has been
  merged.
- **`SONAR HOLD`:** You want existing use to continue but do not want it
  expanded while further review is pending.
- **`SONAR REJECT`:** You do not want the technology used for new work. Put
  migration guidance in the issue when existing users need it.

`PROPOSE` and `ADOPT` need evidence from a pull request in the same repository:

- For `SONAR PROPOSE`, keep a cross-referencing ADR pull request open.
- For `SONAR ADOPT`, merge a cross-referencing ADR pull request.

Make the relationship visible to GitHub by referencing the technology issue in
the pull request, for example with `#123` in its description. Tech Sonar shows
a warning when a `PROPOSE` issue lacks an open supporting pull request or an
`ADOPT` issue lacks a merged one. The warning does not prevent the issue from
appearing.

## Manage categories

Category labels begin with `SONAR CATEGORY `, followed by the displayed name;
for example, `SONAR CATEGORY Databases` appears as `Databases`. Add or remove
these labels in the issue's **Labels** sidebar.

You can assign more than one category, which places the technology in each
corresponding category slice. An issue without a category label appears as
`Uncategorised`.

## Control whether an issue appears

Tech Sonar includes both open and closed issues when they have a Sonar status
label. Closing an issue records its state but does not remove it from the
Sonar. Reopen the issue if you need to resume GitHub discussion.

To remove an issue from the Sonar without deleting its history, remove all five
`SONAR …` status labels. Add an appropriate status label later if you want the
issue to appear again.

Changes to issues, labels, and supporting pull requests start the publishing
workflow. The public Sonar changes only after that workflow finishes
successfully.

For the precise source-data rules, see the
[GitHub issue data model](github-issue-data-model.md).
