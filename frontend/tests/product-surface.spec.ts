import { expect, test, type Page } from "@playwright/test";

const tracks = {
  tracks: [
    { id: "monaco", name: "Monaco", base_lap_time: 72.4, pit_loss: 20.5, degradation_multiplier: 1.2, safety_car_probability: 0.45 },
    { id: "silverstone", name: "Silverstone", base_lap_time: 88.2, pit_loss: 23.0, degradation_multiplier: 0.95, safety_car_probability: 0.2 },
  ],
};

const first = {
  strategy_id: 1,
  strategy: [{ compound: "medium", laps: 12 }, { compound: "hard", laps: 18 }],
  win_probability: 0.625,
  win_percentage: 62.5,
  preference_probability: 0.625,
  preference_percentage: 62.5,
  average_total_time: 2310.125,
  best_case: 2297.4,
  worst_case: 2324.9,
  std_dev: 5.25,
};

const second = {
  strategy_id: 2,
  strategy: [{ compound: "soft", laps: 9 }, { compound: "hard", laps: 21 }],
  win_probability: 0.375,
  win_percentage: 37.5,
  preference_probability: 0.375,
  preference_percentage: 37.5,
  average_total_time: 2314.75,
  best_case: 2300.2,
  worst_case: 2332.6,
  std_dev: 6.1,
};

const simulation = {
  track: "Monaco",
  track_id: "monaco",
  base_lap_time: 72.5,
  pit_loss: 21,
  degradation_multiplier: 1.2,
  total_generated: 46,
  deterministic_candidates_evaluated: 2,
  simulations_per_strategy: 200,
  confidence: "high",
  win_gap_to_second: 25,
  recommendation: "Legacy recommendation text is intentionally not presented.",
  best_strategy: first,
  ranked_strategies: [first, second],
  safety_car_probability: 0.45,
  safety_car_simulations: 91,
  safety_car_rate: 0.455,
  seed: 2026,
};

async function mockSimulation(page: Page, response: unknown = simulation, onRequest?: (body: Record<string, unknown>) => void) {
  await page.route("**/tracks", (route) => route.fulfill({ json: tracks }));
  await page.route("**/monte-carlo/generate", (route) => {
    onRequest?.(route.request().postDataJSON() as Record<string, unknown>);
    return route.fulfill({ json: response });
  });
}

test("root is a concise product entrance with accurate routes and capability status", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByTestId("product-entrance")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Race Strategy Decision Support" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open Historical Workbench" })).toHaveAttribute("href", "/workbench");
  await expect(page.getByRole("link", { name: "Open Scenario Simulation Lab" })).toHaveAttribute("href", "/simulation");
  await expect(page.getByText("Historical RaceState").locator("..")).toContainText("OPERATIONAL");
  await expect(page.getByText("Competitors & Traffic").locator("..")).toContainText("NEXT");
  await expect(page.getByText("Strategy Decision Engine").locator("..")).toContainText("PLANNED");
  await expect(page.getByText("Race Engineer AI")).toHaveCount(0);
  await expect(page.getByText("Historical Decision Replay")).toHaveCount(0);
});

test("simulation lab runs a validated scenario comparison without AI or replay calls", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const requests: string[] = [];
  let submitted: Record<string, unknown> | undefined;
  page.on("request", (request) => requests.push(new URL(request.url()).pathname));
  await mockSimulation(page, simulation, (body) => { submitted = body; });
  await page.goto("/simulation");
  await expect(page.getByRole("heading", { name: "Scenario Simulation Lab" })).toBeVisible();
  await expect(page.getByText("Experimental", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Circuit")).toHaveValue("monaco");
  await page.getByLabel("Total laps").fill("30");
  await page.getByLabel("Base lap time").fill("72.5");
  await page.getByLabel("Pit loss").fill("21");
  await page.getByLabel("Runs per strategy").fill("200");
  await page.getByLabel("Simulation seed").fill("2026");
  await page.getByRole("button", { name: "Run scenario simulation" }).click();

  await expect(page.getByTestId("simulation-results")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Strategy 1" })).toBeVisible();
  await expect(page.getByText("Scenario preference", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("62.50%").first()).toBeVisible();
  await expect(page.getByText("Average simulated race time")).toBeVisible();
  await expect(page.getByText("Generated strategies").locator("..")).toContainText("46");
  await expect(page.getByText("Runs / strategy").locator("..")).toContainText("200");
  await expect(page.getByText("Simulation assumptions")).toBeVisible();
  await expect(page.getByText("Top-two preference gap")).toBeVisible();
  await expect(page.getByText(/confidence/i)).toHaveCount(0);
  await expect(page.getByText(/Race Engineer AI/i)).toHaveCount(0);
  await expect(page.getByText(/Historical Decision Replay/i)).toHaveCount(0);

  const simulationRequest = requests.filter((path) => path === "/monte-carlo/generate");
  expect(simulationRequest).toHaveLength(1);
  expect(submitted).toMatchObject({ track: "monaco", total_laps: 30, base_lap_time: 72.5, pit_loss: 21, simulations: 200, seed: 2026 });
  expect(requests.some((path) => path.startsWith("/ai/") || path.startsWith("/race-engineer/") || path.startsWith("/replay/"))).toBe(false);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByTestId("simulation-results")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await page.setViewportSize({ width: 1440, height: 900 });
});

test("simulation route survives direct navigation and hard refresh", async ({ page }) => {
  await mockSimulation(page);
  const direct = await page.goto("/simulation");
  expect(direct?.status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Scenario Simulation Lab" })).toBeVisible();
  const refresh = await page.reload();
  expect(refresh?.status()).toBe(200);
  await expect(page.getByLabel("Circuit")).toHaveValue("monaco");
});

test("simulation malformed and backend failures are distinct safe states", async ({ page }) => {
  await mockSimulation(page, { ...simulation, ranked_strategies: [] });
  await page.goto("/simulation");
  await page.getByRole("button", { name: "Run scenario simulation" }).click();
  await expect(page.getByRole("alert")).toContainText("malformed simulation data");
  await expect(page.getByTestId("simulation-results")).toHaveCount(0);

  await page.unroute("**/monte-carlo/generate");
  await page.route("**/monte-carlo/generate", (route) => route.fulfill({ status: 503, json: { detail: "Simulation service temporarily unavailable." } }));
  await page.getByRole("button", { name: "Run scenario simulation" }).click();
  await expect(page.getByRole("alert")).toContainText("Simulation service temporarily unavailable.");
});

test("track-load failure is explained without a broken simulation card", async ({ page }) => {
  await page.route("**/tracks", (route) => route.fulfill({ status: 503, json: { detail: "Track catalogue temporarily unavailable." } }));
  await page.goto("/simulation");
  await expect(page.getByRole("alert")).toContainText("Track catalogue temporarily unavailable.");
  await expect(page.getByRole("button", { name: "Run scenario simulation" })).toBeDisabled();
});

test("unknown routes render a safe not-found surface", async ({ page }) => {
  const response = await page.goto("/not-a-racebrain-route");
  expect(response?.status()).toBe(200);
  await expect(page.getByText("404 / UNKNOWN ROUTE")).toBeVisible();
  await expect(page.getByRole("link", { name: "Product entrance" })).toHaveAttribute("href", "/");
});
