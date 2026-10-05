import { expect, test } from "@playwright/test";

test("product entrance fits a 390px viewport", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("product-entrance")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open Historical Workbench" })).toBeVisible();
  const widths = await page.evaluate(() => ({ viewport: window.innerWidth, document: document.documentElement.scrollWidth }));
  expect(widths).toEqual({ viewport: 390, document: 390 });
});

test("simulation controls fit mobile without page-level overflow", async ({ page }) => {
  await page.route("**/tracks", (route) => route.fulfill({ json: { tracks: [{ id: "monaco", name: "Monaco", base_lap_time: 72.4, pit_loss: 20.5, degradation_multiplier: 1.2, safety_car_probability: 0.45 }] } }));
  await page.goto("/simulation");
  await expect(page.getByRole("button", { name: "Run scenario simulation" })).toBeVisible();
  await expect(page.getByLabel("Simulation seed")).toBeVisible();
  const widths = await page.evaluate(() => ({ viewport: window.innerWidth, document: document.documentElement.scrollWidth }));
  expect(widths).toEqual({ viewport: 390, document: 390 });
});
