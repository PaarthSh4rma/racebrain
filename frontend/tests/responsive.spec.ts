import { expect, test } from "@playwright/test";

test("primary experience fits a 390px viewport", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("combobox")).toBeVisible();
  await expect(page.getByRole("button", { name: "Run Strategy Model" })).toBeVisible();

  for (const card of [
    page.getByTestId("simulation-card"),
    page.getByTestId("race-engineer-card"),
    page.getByTestId("historical-card"),
  ]) {
    await expect(card).toBeVisible();
    const bounds = await card.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
  }

  const widths = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));

  expect(widths.viewport).toBe(390);
  expect(widths.document).toBeLessThanOrEqual(widths.viewport);
});
