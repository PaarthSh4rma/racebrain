import { expect, test, type Page } from "@playwright/test";

const session = { session_key: 9523, meeting_key: 1236, year: 2024, event_name: "Monaco Grand Prix", country_name: "Monaco", location: "Monaco", session_name: "Race", session_type: "Race" };
const drivers = [
  { driver_number: 4, full_name: "Lando Norris", name_acronym: "NOR", team_name: "McLaren" },
  { driver_number: 16, full_name: "Charles Leclerc", name_acronym: "LEC", team_name: "Ferrari" },
];
const quality = { level: "degraded", completeness: null, warnings: ["OpenF1 lap date_start is approximate"], missing_fields: [] };
const provenance = (source: string, observed_at: string) => [{ source, observed_at, transformations: [`${source} bounded at cutoff`], assumptions: [], external_ids: [] }];
const car = (number: number, name: string, position: number) => ({
  competitor_id: `competitor:${number}`, observed_at: "2024-05-26T13:57:58Z", driver_name: name,
  position, current_lap: position === 1 ? 10 : 9,
  gap_ahead: position === 1 ? null : { seconds: null, laps: 1 },
  gap_to_leader: position === 1 ? { seconds: 0, laps: null } : { seconds: null, laps: 1 },
  tyre: { compound: position === 1 ? "hard" : "medium", age_laps: position === 1 ? 10 : 9, stint_number: 2 },
  in_pit: null, pit_stop_count: null, data_quality: quality, provenance: provenance("intervals", "2024-05-26T13:57:57Z"),
  external_ids: [{ provider: "OpenF1", resource_type: "driver_number", value: String(number) }],
});
const reconstructed = {
  race_state: {
    session: { name: "Race", event: { name: "Monaco Grand Prix" } }, observation_cutoff: "2024-05-26T13:57:58Z",
    track_status: { status: "green", observed_at: "2024-05-26T13:44:00Z", provenance: provenance("race_control", "2024-05-26T13:44:00Z") },
    weather: { observed_at: "2024-05-26T13:56:59Z", air_temperature_c: 22.1, track_temperature_c: 47.4, humidity_fraction: 0.65, wind_speed_mps: 0.7, rainfall_detected: false },
    competitors: [car(16, "Charles Leclerc", 1), car(4, "Lando Norris", 2)], data_quality: quality, provenance: [],
  },
  diagnostics: { bounded_pit_lane_passages: 16, cache_hits: {} },
};

async function mockWorkbench(page: Page, failState = false, slowState = false) {
  await page.route("**/v2/historical/sessions?year=**", (route) => {
    const year = new URL(route.request().url()).searchParams.get("year");
    return route.fulfill({ json: year === "2024" ? [session] : [] });
  });
  await page.route("**/v2/historical/sessions/9523/drivers", (route) => route.fulfill({ json: drivers }));
  await page.route("**/v2/historical/sessions/9523/drivers/*/decision-laps", (route) => route.fulfill({ json: { session_key: 9523, driver_number: 4, laps: [9, 10] } }));
  await page.route("**/v2/historical/race-state", async (route) => {
    if (slowState) await new Promise((resolve) => setTimeout(resolve, 200));
    if (failState) return route.fulfill({ status: 502, json: { detail: "OpenF1 race data is temporarily unavailable." } });
    return route.fulfill({ json: reconstructed });
  });
}

test("historical workbench renders canonical field and selected-car evidence", async ({ page }) => {
  await mockWorkbench(page);
  await page.goto("/workbench");
  await expect(page.getByLabel("Event")).toHaveValue("9523");
  await expect(page.getByLabel("Focal driver")).toHaveValue("4");
  await page.getByLabel("Focal driver").selectOption("16");
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
  await page.getByRole("button", { name: "Load state" }).click();
  await expect(page.getByRole("heading", { name: "Full field" })).toBeVisible();
  await expect(page.getByLabel("Session", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Session context")).toContainText("Race");
  await expect(page.getByLabel("Session environment")).toContainText("Monaco Grand Prix");
  await expect(page.getByLabel("Session environment")).toContainText("13:57:58.000 UTC");
  const leader = page.getByRole("row").filter({ hasText: "Charles Leclerc" });
  await expect(leader).toContainText("—");
  await expect(leader).toContainText("0.0s");
  const lapped = page.getByRole("row").filter({ hasText: "Lando Norris" });
  await expect(lapped).toContainText("+1 LAP");
  await expect(page.getByTestId("global-quality")).toContainText("degraded");
  await expect(page.getByTestId("global-quality").locator('[data-quality-tone="caution"]')).toBeVisible();
  await expect(page.getByTestId("global-quality")).toContainText("OpenF1 lap date_start is approximate");
  await expect(lapped).toHaveAttribute("data-quality", "degraded");
  await lapped.click();
  await expect(page.getByRole("heading", { name: "Lando Norris" })).toBeVisible();
  await expect(page.getByText("Pit stops", { exact: true })).toHaveCount(0);
  await page.getByText("Provider evidence").click();
  await expect(page.getByText("intervals", { exact: true })).toBeVisible();
});

test("workbench exposes reconstruction loading and safe upstream errors", async ({ page }) => {
  await mockWorkbench(page, true, true);
  await page.goto("/workbench");
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
  await page.getByRole("button", { name: "Load state" }).click();
  await expect(page.getByText("Reconstructing the bounded field…")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("OpenF1 race data is temporarily unavailable.");
});

test("changing season resets incompatible workbench selections", async ({ page }) => {
  await mockWorkbench(page);
  await page.goto("/workbench");
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
  await page.getByLabel("Season").selectOption("2023");
  await expect(page.getByRole("alert")).toContainText("No historical Grand Prix race sessions");
  await expect(page.getByLabel("Event")).toBeDisabled();
  await expect(page.getByLabel("Focal driver")).toBeDisabled();
});

test("malformed discovery responses are explained without fabricated state", async ({ page }) => {
  await page.route("**/v2/historical/sessions?year=**", (route) => route.fulfill({ json: [{ ...session, session_key: "9523" }] }));
  await page.goto("/workbench");
  await expect(page.getByRole("alert")).toContainText("malformed session data");
  await expect(page.getByRole("heading", { name: "Full field" })).toHaveCount(0);
});

test("malformed driver and decision-lap items are rejected", async ({ page }) => {
  await page.route("**/v2/historical/sessions?year=**", (route) => route.fulfill({ json: [session] }));
  await page.route("**/v2/historical/sessions/9523/drivers", (route) => route.fulfill({ json: [{ driver_number: 16, full_name: 99 }] }));
  await page.goto("/workbench");
  await expect(page.getByRole("alert")).toContainText("malformed driver data");

  await page.unroute("**/v2/historical/sessions/9523/drivers");
  await page.route("**/v2/historical/sessions/9523/drivers", (route) => route.fulfill({ json: drivers }));
  await page.route("**/v2/historical/sessions/9523/drivers/*/decision-laps", (route) => route.fulfill({ json: { laps: [10, "11"] } }));
  await page.reload();
  await expect(page.getByRole("alert")).toContainText("malformed decision-lap data");
});

test("malformed nested competitors and optional environment state are rejected", async ({ page }) => {
  await mockWorkbench(page);
  for (const mutate of [
    (payload: typeof reconstructed) => { payload.race_state.competitors[0].observed_at = 42 as unknown as string; },
    (payload: typeof reconstructed) => { payload.race_state.weather!.rainfall_detected = "yes" as unknown as boolean; },
    (payload: typeof reconstructed) => { payload.race_state.track_status!.provenance = "raw" as unknown as ReturnType<typeof provenance>; },
  ]) {
    const payload = structuredClone(reconstructed);
    mutate(payload);
    await page.unroute("**/v2/historical/race-state");
    await page.route("**/v2/historical/race-state", (route) => route.fulfill({ json: payload }));
    await page.goto("/workbench");
    await expect(page.getByLabel("Decision lap")).toHaveValue("10");
    await page.getByRole("button", { name: "Load state" }).click();
    await expect(page.getByRole("alert")).toContainText("malformed historical race-state data");
  }
});

test("good global quality uses restrained positive semantics", async ({ page }) => {
  await mockWorkbench(page);
  const payload = structuredClone(reconstructed);
  payload.race_state.data_quality = { level: "good", completeness: null, warnings: [], missing_fields: [] };
  await page.unroute("**/v2/historical/race-state");
  await page.route("**/v2/historical/race-state", (route) => route.fulfill({ json: payload }));
  await page.goto("/workbench");
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
  await page.getByRole("button", { name: "Load state" }).click();
  await expect(page.getByTestId("global-quality").locator('[data-quality-tone="positive"]')).toBeVisible();
});

test("desktop controls form one aligned operator row", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await mockWorkbench(page);
  await page.goto("/workbench");
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
  const controls = await Promise.all([
    page.getByLabel("Season").boundingBox(), page.getByLabel("Event").boundingBox(),
    page.getByLabel("Session context").boundingBox(), page.getByLabel("Focal driver").boundingBox(),
    page.getByLabel("Decision lap").boundingBox(), page.getByRole("button", { name: "Load state" }).boundingBox(),
  ]);
  const tops = controls.map((box) => box?.y ?? -100);
  expect(Math.max(...tops) - Math.min(...tops)).toBeLessThan(24);
});
