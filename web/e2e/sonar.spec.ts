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

  await page
    .getByRole("combobox", { name: "Status" })
    .selectOption("HOLD");
  await expect(
    page.getByRole("heading", { name: "#4 Meh tech" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "#3 Bad tech" }),
  ).toHaveCount(0);
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
