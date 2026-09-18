import { z } from "zod";

export const statusSchema = z.enum([
  "REJECT",
  "HOLD",
  "EXPLORE",
  "PROPOSE",
  "ADOPT",
]);

const labelSchema = z.strictObject({
  name: z.string(),
  color: z.string(),
  description: z.string().nullable(),
});

const pullRequestSchema = z.strictObject({
  number: z.number().int().positive(),
  title: z.string(),
  url: z.string().url(),
  state: z.enum(["OPEN", "CLOSED", "MERGED"]),
  merged: z.boolean(),
});

const warningSchema = z.strictObject({
  code: z.string(),
  message: z.string(),
  status: statusSchema,
});

const sonarItemSchema = z.strictObject({
  number: z.number().int().positive(),
  title: z.string(),
  url: z.string().url(),
  state: z.enum(["OPEN", "CLOSED"]),
  updatedAt: z.string().datetime(),
  bodyHtml: z.string(),
  labels: z.array(labelSchema),
  statuses: z.array(statusSchema).nonempty(),
  categories: z.array(z.string()).nonempty(),
  pullRequests: z.array(pullRequestSchema),
  warnings: z.array(warningSchema),
});

export const sonarSnapshotSchema = z.strictObject({
  repository: z.string(),
  generatedAt: z.string().datetime(),
  items: z.array(sonarItemSchema),
});

export type Status = z.infer<typeof statusSchema>;
export type SonarSnapshot = z.infer<typeof sonarSnapshotSchema>;
export type SonarItem = SonarSnapshot["items"][number];

export function parseSnapshot(value: unknown): SonarSnapshot {
  return sonarSnapshotSchema.parse(value);
}

export async function loadSnapshot(
  fetcher: typeof fetch = fetch,
): Promise<SonarSnapshot> {
  const response = await fetcher("/sonar.json");
  if (!response.ok) {
    throw new Error(`Unable to load sonar.json: HTTP ${response.status}`);
  }

  return parseSnapshot(await response.json());
}
