import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { snapshotFixture } from "../test/fixtures";
import { STATUS_ORDER } from "./geometry";
import { SonarView } from "./SonarView";

describe("SonarView", () => {
  it("renders status bands, their key, and category guides", () => {
    const { container } = render(
      <SonarView items={snapshotFixture.items} />,
    );

    expect(container.querySelectorAll("[data-status-band]")).toHaveLength(5);

    const key = screen.getByRole("list", { name: "Status bands" });
    expect(within(key).getAllByRole("listitem")).toHaveLength(5);
    for (const status of STATUS_ORDER) {
      expect(within(key).getByText(status)).toBeInTheDocument();
    }

    expect(container.querySelectorAll("[data-category-separator]")).toHaveLength(
      2,
    );
    expect(screen.getByText("AI", { selector: "text" })).toBeInTheDocument();
    expect(screen.getByText("WEB", { selector: "text" })).toBeInTheDocument();
  });

  it("renders every visual placement as an accessible numbered link", () => {
    render(<SonarView items={snapshotFixture.items} />);

    const links = screen.getAllByRole("link", {
      name: /#3 Generate validated static Sonar content/,
    });
    expect(links).toHaveLength(4);
    for (const link of links) {
      expect(link).toHaveAttribute("href", "/#/items/3");
      expect(within(link).getByText("3")).toBeInTheDocument();
    }
  });

  it("shows one title tooltip for hover and focus", async () => {
    const user = userEvent.setup();
    render(<SonarView items={snapshotFixture.items} />);
    const link = screen.getAllByRole("link", { name: /#3 / })[0];

    await user.hover(link);
    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Generate validated static Sonar content",
    );

    await user.unhover(link);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    await user.tab();
    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Generate validated static Sonar content",
    );

    fireEvent.blur(document.activeElement!);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("keeps the tooltip while focus remains after mouse leave", async () => {
    const user = userEvent.setup();
    render(<SonarView items={snapshotFixture.items} />);
    const link = screen.getAllByRole("link", { name: /#3 / })[0];

    fireEvent.focus(link);
    await user.hover(link);
    await user.unhover(link);

    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Generate validated static Sonar content",
    );

    fireEvent.blur(link);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("keeps the tooltip while hover remains after blur", async () => {
    const user = userEvent.setup();
    render(<SonarView items={snapshotFixture.items} />);
    const link = screen.getAllByRole("link", { name: /#3 / })[0];

    await user.hover(link);
    fireEvent.focus(link);
    fireEvent.blur(link);

    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Generate validated static Sonar content",
    );

    await user.unhover(link);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("keeps all bands visible when no items match", () => {
    const { container } = render(<SonarView items={[]} />);

    expect(container.querySelectorAll("[data-status-band]")).toHaveLength(5);
    expect(
      screen.getByText("No Sonar items match these filters."),
    ).toBeInTheDocument();
  });
});
