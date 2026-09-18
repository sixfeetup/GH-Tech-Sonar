import type { SonarItem, Status } from "../data/sonar";

export const STATUS_ORDER: Status[] = [
  "ADOPT",
  "PROPOSE",
  "EXPLORE",
  "HOLD",
  "REJECT",
];

export interface SonarBand {
  status: Status;
  count: number;
  innerRadius: number;
  outerRadius: number;
}

export interface CategorySlice {
  category: string;
  count: number;
  startAngle: number;
  endAngle: number;
}

export interface SonarPlacement {
  number: number;
  status: Status;
  category: string;
  x: number;
  y: number;
  radius: number;
  item: SonarItem;
}

export interface SonarLayout {
  radius: number;
  bands: SonarBand[];
  categories: CategorySlice[];
  placements: SonarPlacement[];
}

interface ExpandedPlacement {
  status: Status;
  category: string;
  item: SonarItem;
}

interface SlotGrid {
  rows: number;
  columns: number;
  radialSpacing: number;
  angularSpacing: number;
}

function expandItems(items: SonarItem[]): ExpandedPlacement[] {
  return items.flatMap((item) =>
    item.statuses.flatMap((status) =>
      item.categories.map((category) => ({
        status,
        category,
        item,
      })),
    ),
  );
}

function createBands(
  placements: ExpandedPlacement[],
  radius: number,
): SonarBand[] {
  const placementCounts: Record<Status, number> = {
    ADOPT: 0,
    PROPOSE: 0,
    EXPLORE: 0,
    HOLD: 0,
    REJECT: 0,
  };
  for (const placement of placements) {
    placementCounts[placement.status] += 1;
  }

  const counts = STATUS_ORDER.map((status) => placementCounts[status] + 1);
  const totalCount = counts.reduce((total, count) => total + count, 0);
  let cumulativeCount = 0;

  return STATUS_ORDER.map((status, index) => {
    const innerRadius = radius * Math.sqrt(cumulativeCount / totalCount);
    cumulativeCount += counts[index];
    const outerRadius = radius * Math.sqrt(cumulativeCount / totalCount);
    return {
      status,
      count: counts[index],
      innerRadius,
      outerRadius,
    };
  });
}

function createCategories(
  placements: ExpandedPlacement[],
): CategorySlice[] {
  const categoryNames = [
    ...new Set(placements.map((placement) => placement.category)),
  ].sort();
  const counts = categoryNames.map((category) => {
    const statusCounts = STATUS_ORDER.map(
      (status) =>
        placements.filter(
          (placement) =>
            placement.category === category && placement.status === status,
        ).length,
    );
    return 1 + Math.max(...statusCounts);
  });
  const totalCount = counts.reduce((total, count) => total + count, 0);
  let startAngle = 0;

  return categoryNames.map((category, index) => {
    const endAngle = startAngle + (counts[index] / totalCount) * 360;
    const slice = {
      category,
      count: counts[index],
      startAngle,
      endAngle,
    };
    startAngle = endAngle;
    return slice;
  });
}

function chooseSlotGrid(
  count: number,
  band: SonarBand,
  category: CategorySlice,
): SlotGrid {
  const radialWidth = band.outerRadius - band.innerRadius;
  const midpointRadius = (band.innerRadius + band.outerRadius) / 2;
  const angleRadians =
    ((category.endAngle - category.startAngle) * Math.PI) / 180;
  let bestGrid: SlotGrid | undefined;
  let bestMinimumSpacing = -Infinity;

  for (let rows = 1; rows <= count; rows += 1) {
    const columns = Math.ceil(count / rows);
    const radialSpacing = radialWidth / rows;
    const angularSpacing = (midpointRadius * angleRadians) / columns;
    const minimumSpacing = Math.min(radialSpacing, angularSpacing);

    if (minimumSpacing > bestMinimumSpacing) {
      bestMinimumSpacing = minimumSpacing;
      bestGrid = {
        rows,
        columns,
        radialSpacing,
        angularSpacing,
      };
    }
  }

  return bestGrid!;
}

function placeCell(
  placements: ExpandedPlacement[],
  band: SonarBand,
  category: CategorySlice,
): SonarPlacement[] {
  const sortedPlacements = [...placements].sort(
    (first, second) => first.item.number - second.item.number,
  );
  const grid = chooseSlotGrid(sortedPlacements.length, band, category);
  const angularSlotWidth =
    (category.endAngle - category.startAngle) / grid.columns;
  const dotRadius = Math.min(
    15,
    0.32 * Math.min(grid.radialSpacing, grid.angularSpacing),
  );

  return sortedPlacements.map((placement, index) => {
    const row = Math.floor(index / grid.columns);
    const column = index % grid.columns;
    const radialPosition =
      band.innerRadius + (row + 0.5) * grid.radialSpacing;
    const angle =
      category.startAngle + (column + 0.5) * angularSlotWidth;
    const angleRadians = (angle * Math.PI) / 180;

    return {
      number: placement.item.number,
      status: placement.status,
      category: placement.category,
      x: radialPosition * Math.cos(angleRadians),
      y: radialPosition * Math.sin(angleRadians),
      radius: dotRadius,
      item: placement.item,
    };
  });
}

export function layoutSonar(
  items: SonarItem[],
  radius: number,
): SonarLayout {
  const expandedPlacements = expandItems(items);
  const bands = createBands(expandedPlacements, radius);
  const categories = createCategories(expandedPlacements);
  const placements: SonarPlacement[] = [];

  for (const band of bands) {
    for (const category of categories) {
      const cellPlacements = expandedPlacements.filter(
        (placement) =>
          placement.status === band.status &&
          placement.category === category.category,
      );
      if (cellPlacements.length > 0) {
        placements.push(...placeCell(cellPlacements, band, category));
      }
    }
  }

  return {
    radius,
    bands,
    categories,
    placements,
  };
}
