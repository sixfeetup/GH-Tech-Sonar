import { expect, test, type Page } from "@playwright/test";

async function loadSonar(page: Page) {
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "sixfeetup/GH-Tech-Sonar-Test: 7 items",
    }),
  ).toBeVisible();
}

async function selectIssueFour(page: Page) {
  await page
    .getByRole("combobox", { name: "Category" })
    .selectOption("AI");
  await page
    .getByRole("combobox", { name: "Status" })
    .selectOption("HOLD");
}

async function expectNoHorizontalOverflow(page: Page) {
  const hasHorizontalOverflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
}

test("loads the fixture and toggles between Sonar and List", async ({
  page,
}) => {
  await loadSonar(page);

  await expect(
    page.getByRole("region", { name: "Sonar view" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "List" }).click();
  await expect(
    page.getByRole("heading", { name: "#10 We should do this instead" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sonar" }).click();
  await expect(
    page.getByRole("region", { name: "Sonar view" }),
  ).toBeVisible();
});

test("positions the hovered title above its issue", async ({ page }) => {
  await loadSonar(page);

  const issue = page.getByRole("link", { name: /^#4 Meh tech/ });
  await issue.hover();

  const dotBox = await issue.locator("circle").boundingBox();
  const tooltipBox = await page.getByRole("tooltip").boundingBox();
  expect(dotBox).not.toBeNull();
  expect(tooltipBox).not.toBeNull();
  expect(tooltipBox!.y + tooltipBox!.height).toBeLessThan(dotBox!.y - 4);
  expect(tooltipBox!.x + tooltipBox!.width / 2).toBeCloseTo(
    dotBox!.x + dotBox!.width / 2,
    0,
  );
});

test("places the desktop legend next to the radar", async (
  { page },
  testInfo,
) => {
  test.skip(testInfo.project.name !== "desktop");
  await loadSonar(page);

  const radarBox = await page
    .locator('[data-status-band="REJECT"]')
    .boundingBox();
  const legendBox = await page
    .getByRole("list", { name: "Status bands" })
    .boundingBox();
  expect(radarBox).not.toBeNull();
  expect(legendBox).not.toBeNull();

  const gap = legendBox!.x - (radarBox!.x + radarBox!.width);
  expect(gap).toBeGreaterThanOrEqual(0);
  expect(gap).toBeLessThanOrEqual(24);
});

test("renders application surfaces with a dark theme", async ({ page }) => {
  await loadSonar(page);

  const colors = await page.evaluate(() => ({
    background: getComputedStyle(document.body).backgroundColor,
    text: getComputedStyle(document.body).color,
    control: getComputedStyle(document.querySelector("select")!).backgroundColor,
    legend: getComputedStyle(
      document.querySelector<HTMLElement>(".sonar-key")!,
    ).backgroundColor,
    radar: getComputedStyle(
      document.querySelector<SVGPathElement>(".sonar-band")!,
    ).fill,
  }));
  const channels = (color: string) =>
    color.match(/[\d.]+/g)!.slice(0, 3).map(Number);

  for (const surface of [
    colors.background,
    colors.control,
    colors.legend,
    colors.radar,
  ]) {
    expect(Math.max(...channels(surface))).toBeLessThan(96);
  }
  expect(Math.min(...channels(colors.text))).toBeGreaterThan(160);
});

test("filters both views by category and status", async ({ page }) => {
  await loadSonar(page);
  await page
    .getByRole("combobox", { name: "Category" })
    .selectOption("AI");

  const sonar = page.getByRole("region", { name: "Sonar view" });
  await expect(sonar.getByRole("link")).toHaveCount(2);
  await expect(
    sonar.getByRole("link", { name: /^#3 Bad tech/ }),
  ).toBeVisible();
  await expect(
    sonar.getByRole("link", { name: /^#4 Meh tech/ }),
  ).toBeVisible();
  await expect(sonar.getByText("AI", { exact: true })).toBeVisible();
  await expect(
    sonar.getByText("Uncategorised", { exact: true }),
  ).toHaveCount(0);
  await expect(sonar.getByText("WEB", { exact: true })).toHaveCount(0);

  await page.getByRole("button", { name: "List" }).click();
  await expect(
    page.getByRole("heading", { name: "#4 Meh tech" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "#3 Bad tech" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /^#2 / }),
  ).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 2 })).toHaveCount(2);

  await page
    .getByRole("combobox", { name: "Status" })
    .selectOption("HOLD");
  await expect(
    page.getByRole("heading", { name: "#4 Meh tech" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "#3 Bad tech" }),
  ).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 2 })).toHaveCount(1);
});

test("filters both views by updated date", async ({ page }) => {
  await loadSonar(page);
  await page
    .getByRole("textbox", { name: "Updated since" })
    .fill("2026-09-18");

  const sonar = page.getByRole("region", { name: "Sonar view" });
  await expect(sonar.getByRole("link")).toHaveCount(5);
  await expect(
    sonar.getByRole("link", { name: /^#2 Neat tech/ }),
  ).toHaveCount(0);
  await expect(
    sonar.getByRole("link", { name: /^#5 We should do this/ }),
  ).toHaveCount(0);

  await page.getByRole("button", { name: "List" }).click();
  await expect(
    page.getByRole("heading", { name: /^#2 / }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: /^#5 / }),
  ).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 2 })).toHaveCount(5);
});

test("desktop activation opens details in a popup", async (
  { page },
  testInfo,
) => {
  test.skip(testInfo.project.name !== "desktop");
  await loadSonar(page);
  await selectIssueFour(page);

  const popupPromise = page.waitForEvent("popup");
  await page.getByRole("link", { name: /^#4 Meh tech/ }).click();
  const popup = await popupPromise;

  await expect(popup).toHaveURL(/\/#\/items\/4$/);
  await expect(
    popup.getByRole("heading", { name: "Meh tech", level: 1 }),
  ).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await expectNoHorizontalOverflow(popup);
});

test("mobile activation preserves the filtered view after Back", async (
  { page },
  testInfo,
) => {
  test.skip(testInfo.project.name !== "mobile");
  await loadSonar(page);
  await selectIssueFour(page);

  await page.getByRole("link", { name: /^#4 Meh tech/ }).click();
  await expect(page).toHaveURL(/\/#\/items\/4$/);
  await expect(
    page.getByRole("heading", { name: "Meh tech", level: 1 }),
  ).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.getByRole("button", { name: "Back" }).click();
  await expect(
    page.getByRole("region", { name: "Sonar view" }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Category" }),
  ).toHaveValue("AI");
  await expect(
    page.getByRole("combobox", { name: "Status" }),
  ).toHaveValue("HOLD");
  await expect(
    page.getByRole("link", { name: /^#4 Meh tech/ }),
  ).toBeVisible();
  await expectNoHorizontalOverflow(page);
});
