import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { snapshotFixture } from "./test/fixtures";

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    headers: { "Content-Type": "application/json" },
  });
}

function renderApp(): void {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );
}

describe("App loading", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a loading state while the snapshot request is pending", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => undefined)));

    renderApp();

    expect(screen.getByText("Loading Tech Sonar…")).toBeVisible();
  });

  it("shows a fetch failure with a Retry button", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("missing", { status: 503 })),
    );

    renderApp();

    expect(
      await screen.findByText(
        "Unable to load Tech Sonar: Unable to load sonar.json: HTTP 503",
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Retry" })).toBeVisible();
  });

  it("shows a schema failure with a Retry button", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({})));

    renderApp();

    const message = await screen.findByText(/Unable to load Tech Sonar:/);
    expect(message).toHaveTextContent("repository");
    expect(screen.getByRole("button", { name: "Retry" })).toBeVisible();
  });

  it("retries loading after a failure", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response("missing", { status: 503 }))
      .mockResolvedValueOnce(jsonResponse(snapshotFixture));
    vi.stubGlobal("fetch", fetcher);
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByRole("button", { name: "Retry" }));

    expect(
      await screen.findByRole("heading", {
        name: "sixfeetup/GH-Tech-Sonar: 1 items",
      }),
    ).toBeVisible();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("shows links for contributing to the source repository", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(snapshotFixture)),
    );
    const user = userEvent.setup();
    renderApp();

    await user.click(
      await screen.findByRole("button", { name: "Contribute" }),
    );

    expect(screen.getByRole("dialog", { name: "Contribute" })).toBeVisible();
    const issueLink = screen.getByRole("link", { name: "Technology issue" });
    expect(issueLink).toHaveAttribute(
      "href",
      "https://github.com/sixfeetup/GH-Tech-Sonar/issues/new?template=technology.yml",
    );
    const documentationLink = screen.getByRole("link", {
      name: "Tech Sonar documentation",
    });
    expect(documentationLink).toHaveAttribute(
      "href",
      "https://github.com/sixfeetup/GH-Tech-Sonar/blob/main/docs/using-tech-sonar.md",
    );
    for (const link of [issueLink, documentationLink]) {
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noreferrer");
    }
  });

  it("closes contribution details and returns focus to Contribute", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(snapshotFixture)),
    );
    const user = userEvent.setup();
    renderApp();
    const contribute = await screen.findByRole("button", {
      name: "Contribute",
    });
    await user.click(contribute);

    await user.click(screen.getByRole("button", { name: "Close" }));

    expect(screen.queryByRole("dialog", { name: "Contribute" })).toBeNull();
    expect(contribute).toHaveFocus();
  });

  it("closes contribution details with Escape", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(snapshotFixture)),
    );
    const user = userEvent.setup();
    renderApp();
    const contribute = await screen.findByRole("button", {
      name: "Contribute",
    });
    await user.click(contribute);

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog", { name: "Contribute" })).toBeNull();
    expect(contribute).toHaveFocus();
  });
});
