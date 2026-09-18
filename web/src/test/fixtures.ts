import type { SonarSnapshot } from "../data/sonar";

export const snapshotFixture: SonarSnapshot = {
  repository: "sixfeetup/GH-Tech-Sonar",
  generatedAt: "2026-09-15T20:30:00Z",
  items: [
    {
      number: 3,
      title: "Generate validated static Sonar content",
      url: "https://github.com/sixfeetup/GH-Tech-Sonar/issues/3",
      state: "OPEN",
      updatedAt: "2026-09-15T18:00:00Z",
      bodyHtml: "<p>Evaluate this technology.</p>",
      labels: [
        {
          name: "SONAR CATEGORY AI",
          color: "65435f",
          description: "Artificial intelligence",
        },
      ],
      statuses: ["EXPLORE", "PROPOSE"],
      categories: ["AI", "WEB"],
      pullRequests: [
        {
          number: 10,
          title: "Approve the ADR",
          url: "https://github.com/sixfeetup/GH-Tech-Sonar/pull/10",
          state: "OPEN",
          merged: false,
        },
      ],
      warnings: [
        {
          code: "missing-propose-evidence",
          message: "Issue 3 requires an open pull request.",
          status: "PROPOSE",
        },
      ],
    },
  ],
};
