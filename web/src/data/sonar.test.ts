import { describe, expect, it, vi } from "vitest";

import { loadSnapshot, parseSnapshot } from "./sonar";
import { snapshotFixture } from "../test/fixtures";

describe("parseSnapshot", () => {
  it("accepts the generated snapshot contract", () => {
    expect(parseSnapshot(snapshotFixture)).toEqual(snapshotFixture);
  });

  it("rejects an unknown status", () => {
    const invalid = {
      ...structuredClone(snapshotFixture),
      items: [
        {
          ...structuredClone(snapshotFixture.items[0]),
          statuses: ["UNKNOWN"],
        },
      ],
    };

    expect(() => parseSnapshot(invalid)).toThrow(/status/i);
  });

  it("rejects an item with missing keys", () => {
    const { title: _title, ...itemWithoutTitle } = structuredClone(
      snapshotFixture.items[0],
    );
    const invalid = {
      ...structuredClone(snapshotFixture),
      items: [itemWithoutTitle],
    };

    expect(() => parseSnapshot(invalid)).toThrow(/title/i);
  });

  it("rejects malformed warnings", () => {
    const invalid = {
      ...structuredClone(snapshotFixture),
      items: [
        {
          ...structuredClone(snapshotFixture.items[0]),
          warnings: [
            {
              code: "missing-propose-evidence",
              message: "Missing status",
            },
          ],
        },
      ],
    };

    expect(() => parseSnapshot(invalid)).toThrow(/status/i);
  });
});

describe("loadSnapshot", () => {
  it("reports an unsuccessful snapshot response", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response("missing", {
        status: 404,
      }),
    );

    await expect(loadSnapshot(fetcher)).rejects.toThrow(/404/);
  });
});
