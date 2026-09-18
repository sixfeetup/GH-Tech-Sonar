import { describe, expect, it } from "vitest";

import type { SonarItem } from "../data/sonar";
import { snapshotFixture } from "../test/fixtures";
import { layoutSonar, STATUS_ORDER } from "./geometry";

const baseItem = snapshotFixture.items[0];
const items: SonarItem[] = [
  {
    ...baseItem,
    number: 3,
    statuses: ["EXPLORE", "PROPOSE"],
    categories: ["AI", "WEB"],
  },
  {
    ...baseItem,
    number: 2,
    statuses: ["EXPLORE"],
    categories: ["AI"],
  },
];

function normalizedAngle(x: number, y: number): number {
  const degrees = (Math.atan2(y, x) * 180) / Math.PI;
  return degrees < 0 ? degrees + 360 : degrees;
}

describe("layoutSonar", () => {
  it("sizes status bands from expanded placement counts", () => {
    const radius = 200;
    const layout = layoutSonar(items, radius);

    expect(layout.bands.map((band) => band.status)).toEqual(STATUS_ORDER);
    expect(layout.bands.map((band) => band.count)).toEqual([1, 3, 4, 1, 1]);

    const totalCount = layout.bands.reduce(
      (total, band) => total + band.count,
      0,
    );
    for (const band of layout.bands) {
      const squaredArea =
        band.outerRadius ** 2 - band.innerRadius ** 2;
      expect(squaredArea / radius ** 2).toBeCloseTo(
        band.count / totalCount,
      );
    }

    expect(layout.bands.at(-1)?.outerRadius).toBeCloseTo(radius);
    for (const band of layout.bands) {
      expect(band.outerRadius).toBeGreaterThan(band.innerRadius);
    }
  });

  it("sizes alphabetized category slices for their densest bands", () => {
    const { categories } = layoutSonar(items, 200);

    expect(categories.map((category) => category.category)).toEqual([
      "AI",
      "WEB",
    ]);
    expect(categories.map((category) => category.count)).toEqual([3, 2]);

    const aiSpan = categories[0].endAngle - categories[0].startAngle;
    const webSpan = categories[1].endAngle - categories[1].startAngle;
    expect(aiSpan / webSpan).toBeCloseTo(3 / 2);
    expect(categories[0].startAngle).toBeCloseTo(0);
    expect(categories.at(-1)?.endAngle).toBeCloseTo(360);
  });

  it("expands multi-valued items and sorts placements within each cell", () => {
    const { placements } = layoutSonar(items, 200);

    expect(placements).toHaveLength(5);
    expect(
      placements
        .filter(
          (placement) =>
            placement.status === "EXPLORE" && placement.category === "AI",
        )
        .map((placement) => placement.number),
    ).toEqual([2, 3]);
    expect(
      placements
        .filter((placement) => placement.number === 3)
        .map((placement) => [placement.status, placement.category]),
    ).toEqual([
      ["PROPOSE", "AI"],
      ["PROPOSE", "WEB"],
      ["EXPLORE", "AI"],
      ["EXPLORE", "WEB"],
    ]);
  });

  it("returns byte-equivalent placements on repeated calls", () => {
    expect(JSON.stringify(layoutSonar(items, 200).placements)).toBe(
      JSON.stringify(layoutSonar(items, 200).placements),
    );
  });

  it("keeps centers inside their annular sectors", () => {
    const layout = layoutSonar(items, 200);

    for (const placement of layout.placements) {
      const band = layout.bands.find(
        (candidate) => candidate.status === placement.status,
      );
      const category = layout.categories.find(
        (candidate) => candidate.category === placement.category,
      );
      expect(band).toBeDefined();
      expect(category).toBeDefined();

      const radialPosition = Math.hypot(placement.x, placement.y);
      const angle = normalizedAngle(placement.x, placement.y);
      expect(radialPosition).toBeGreaterThan(band!.innerRadius);
      expect(radialPosition).toBeLessThan(band!.outerRadius);
      expect(angle).toBeGreaterThan(category!.startAngle);
      expect(angle).toBeLessThan(category!.endAngle);
    }
  });

  it("does not overlap dots within a cell", () => {
    const { placements } = layoutSonar(items, 200);

    for (const [index, first] of placements.entries()) {
      for (const second of placements.slice(index + 1)) {
        if (
          first.status !== second.status ||
          first.category !== second.category
        ) {
          continue;
        }

        const centerDistance = Math.hypot(
          first.x - second.x,
          first.y - second.y,
        );
        expect(centerDistance).toBeGreaterThanOrEqual(
          first.radius + second.radius,
        );
      }
    }
  });
});
