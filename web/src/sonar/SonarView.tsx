import { useEffect, useRef, useState } from "react";

import type { SonarItem, Status } from "../data/sonar";
import { ItemLink } from "../details/ItemLink";
import {
  layoutSonar,
  STATUS_ORDER,
  type SonarBand,
  type SonarPlacement,
} from "./geometry";

export const STATUS_COLORS: Record<Status, string> = {
  REJECT: "#b60205",
  HOLD: "#6a737d",
  EXPLORE: "#1d76db",
  PROPOSE: "#fbca04",
  ADOPT: "#0e8a16",
};

interface SonarViewProps {
  items: SonarItem[];
}

interface Point {
  x: number;
  y: number;
}

const DEFAULT_SIZE = 600;
const LABEL_MARGIN = 42;

function pointAt(radius: number, angle: number): Point {
  const radians = (angle * Math.PI) / 180;
  return {
    x: radius * Math.cos(radians),
    y: radius * Math.sin(radians),
  };
}

function bandPath({ innerRadius, outerRadius }: SonarBand): string {
  const outer = [
    `M ${outerRadius} 0`,
    `A ${outerRadius} ${outerRadius} 0 1 1 ${-outerRadius} 0`,
    `A ${outerRadius} ${outerRadius} 0 1 1 ${outerRadius} 0`,
  ];

  if (innerRadius === 0) {
    return [...outer, "L 0 0", "Z"].join(" ");
  }

  return [
    ...outer,
    `L ${innerRadius} 0`,
    `A ${innerRadius} ${innerRadius} 0 1 0 ${-innerRadius} 0`,
    `A ${innerRadius} ${innerRadius} 0 1 0 ${innerRadius} 0`,
    "Z",
  ].join(" ");
}

export function SonarView({ items }: SonarViewProps) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState(DEFAULT_SIZE);
  const [hoveredPlacement, setHoveredPlacement] =
    useState<SonarPlacement | null>(null);
  const [focusedPlacement, setFocusedPlacement] =
    useState<SonarPlacement | null>(null);

  useEffect(() => {
    const plot = plotRef.current;
    if (!plot) {
      return;
    }

    const observer = new ResizeObserver(([entry]) => {
      setSize(Math.max(entry.contentRect.width, 1));
    });
    observer.observe(plot);
    return () => observer.disconnect();
  }, []);

  const radius = Math.max(size / 2 - LABEL_MARGIN, 1);
  const layout = layoutSonar(items, radius);
  const center = size / 2;
  const tooltipPlacement = hoveredPlacement ?? focusedPlacement;

  return (
    <section className="sonar-view" aria-label="Sonar view">
      <div className="sonar-plot" ref={plotRef}>
        <svg
          aria-label="Tech Sonar"
          className="sonar-svg"
          role="group"
          viewBox={`0 0 ${size} ${size}`}
        >
          <g transform={`translate(${center} ${center})`}>
            {layout.bands.map((band) => (
              <path
                aria-label={`${band.status} band`}
                className="sonar-band"
                d={bandPath(band)}
                data-status-band={band.status}
                key={band.status}
                role="img"
              />
            ))}

            {layout.categories.map((category) => {
              const end = pointAt(layout.radius, category.startAngle);
              const label = pointAt(
                layout.radius + 24,
                (category.startAngle + category.endAngle) / 2,
              );
              return (
                <g key={category.category}>
                  <line
                    className="category-separator"
                    data-category-separator={category.category}
                    x1="0"
                    x2={end.x}
                    y1="0"
                    y2={end.y}
                  />
                  <text
                    className="category-label"
                    textAnchor="middle"
                    x={label.x}
                    y={label.y}
                  >
                    {category.category}
                  </text>
                </g>
              );
            })}

            {layout.placements.map((placement) => {
              const key = [
                placement.number,
                placement.status,
                placement.category,
              ].join("-");
              const accessibleName = `#${placement.number} ${placement.item.title} — ${placement.status}, ${placement.category}`;
              return (
                <ItemLink
                  aria-label={accessibleName}
                  className="sonar-dot"
                  key={key}
                  number={placement.number}
                  onBlur={() => setFocusedPlacement(null)}
                  onFocus={() => setFocusedPlacement(placement)}
                  onMouseEnter={() => setHoveredPlacement(placement)}
                  onMouseLeave={() => setHoveredPlacement(null)}
                >
                  <circle
                    cx={placement.x}
                    cy={placement.y}
                    r={placement.radius}
                  />
                  <text
                    aria-hidden="true"
                    dominantBaseline="central"
                    textAnchor="middle"
                    x={placement.x}
                    y={placement.y}
                  >
                    {placement.number}
                  </text>
                </ItemLink>
              );
            })}
          </g>
        </svg>
        {items.length === 0 && (
          <p className="sonar-empty">
            No Sonar items match these filters.
          </p>
        )}
        {tooltipPlacement !== null && (
          <div
            className="sonar-tooltip"
            role="tooltip"
            style={{
              left: center + tooltipPlacement.x,
              top:
                center +
                tooltipPlacement.y -
                tooltipPlacement.radius -
                8,
            }}
          >
            {tooltipPlacement.item.title}
          </div>
        )}
      </div>

      <ul aria-label="Status bands" className="sonar-key">
        {STATUS_ORDER.map((status) => (
          <li key={status}>
            <span
              aria-hidden="true"
              className="sonar-key-swatch"
              style={{ backgroundColor: STATUS_COLORS[status] }}
            />
            {status}
          </li>
        ))}
      </ul>
    </section>
  );
}
