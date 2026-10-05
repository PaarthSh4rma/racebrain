import { expect, test, type Page } from "@playwright/test";

const session = { session_key: 9523, meeting_key: 1236, year: 2024, event_name: "Monaco Grand Prix", country_name: "Monaco", location: "Monaco", session_name: "Race", session_type: "Race" };
const drivers = [
  { driver_number: 4, full_name: "Lando Norris", name_acronym: "NOR", team_name: "McLaren" },
  { driver_number: 16, full_name: "Charles Leclerc", name_acronym: "LEC", team_name: "Ferrari" },
];
const quality = { level: "degraded", completeness: null, warnings: ["OpenF1 lap completion is approximate"], missing_fields: [] };
const provenance = (source: string, observed_at: string | null) => [{ source, observed_at, transformations: [`${source} bounded at cutoff`], assumptions: [], external_ids: [] }];
const model = (model_name: string, hash: string) => ({ model_name, version: "0.1.0", config_hash: `sha256:${hash.padEnd(64, "0")}` });
const paceModel = model("representative-clean-pace", "pace");
const tyreModel = model("empirical-tyre-age-slope", "tyre");
const robustnessModel = model("empirical-model-robustness", "robust");
const evidenceWindow = { started_at: "2024-05-26T13:50:00Z", ended_at: "2024-05-26T13:57:58Z", first_lap: 4, last_lap: 10 };
const selectionAudit = { hard_exclusions: [{ reason: "pit_out", lap_count: 1 }], warning_exclusions: [] };
const car = (number: number, name: string, position: number) => ({
  competitor_id: `competitor:${number}`, observed_at: "2024-05-26T13:57:58Z", driver_name: name,
  position, current_lap: position === 1 ? 10 : 9,
  gap_ahead: position === 1 ? null : { seconds: null, laps: 1 },
  gap_to_leader: position === 1 ? { seconds: 0, laps: null } : { seconds: null, laps: 1 },
  tyre: { compound: position === 1 ? "hard" : "soft", age_laps: position === 1 ? 10 : 2, stint_number: position === 1 ? 1 : 2 },
  in_pit: null, pit_stop_count: null, data_quality: quality, provenance: provenance("intervals", "2024-05-26T13:57:57Z"),
  external_ids: [{ provider: "OpenF1", resource_type: "driver_number", value: String(number) }],
});

function fitDiagnostics(competitor_id: string, model_version = paceModel) {
  return { competitor_id, as_of: "2024-05-26T13:57:58Z", candidate_laps: 8, included_laps: 7, excluded_laps: 1, residual_median_s: 0.01, residual_median_absolute_s: 0.2, warnings: quality.warnings, model_version, data_quality: quality, provenance: provenance(model_version.model_name, null) };
}

function paceResult(competitor_id: string, value: number) {
  const diagnostics = fitDiagnostics(competitor_id);
  return {
    competitor_id, as_of: diagnostics.as_of, point_model_version: paceModel, robustness_model_version: robustnessModel,
    point_fit: { competitor_id, estimate: { value, unit: "s/lap", model_version: paceModel, uncertainty: null, confidence: "unknown", assumptions: [], provenance: provenance("pace", null), competitor_id, as_of: diagnostics.as_of, sample_count: 7, evidence_window: evidenceWindow, data_quality: quality, limitations: ["No fuel correction"] }, diagnostics, selection_audit: selectionAudit, unavailable_reason: null },
    diagnostics: { quantile_method: "linear_interpolation", quantiles: { p10: value - 1.1, p50: value, p90: value + 1.3, sample_count: 7 }, minimum_lap_time_s: value - 1.5, maximum_lap_time_s: value + 1.5, p90_p10_spread_s: 2.4 },
    unavailable_reason: null, data_quality: quality, provenance: provenance("pace robustness", null), limitations: ["Empirical included-lap spread is non-probabilistic."],
  };
}

function availableTyre(competitor_id: string) {
  const diagnostics = { ...fitDiagnostics(competitor_id, tyreModel), compound: "hard", stint_number: 1, minimum_tyre_age_laps: 4, maximum_tyre_age_laps: 10, tyre_age_span_laps: 6, intercept_s: 79.1 };
  return {
    competitor_id, as_of: diagnostics.as_of, point_model_version: tyreModel, robustness_model_version: robustnessModel,
    point_fit: { competitor_id, estimate: { value: 0.054, unit: "s/lap/lap", model_version: tyreModel, uncertainty: null, confidence: "unknown", assumptions: [], provenance: provenance("tyre", null), competitor_id, as_of: diagnostics.as_of, sample_count: 7, evidence_window: evidenceWindow, data_quality: quality, limitations: ["No fuel correction"], compound: "hard", stint_number: 1, minimum_tyre_age_laps: 4, maximum_tyre_age_laps: 10 }, diagnostics, selection_audit: selectionAudit, unavailable_reason: null },
    diagnostics: { nominal_slope_s_per_lap_per_lap: 0.054, nominal_sign: "positive", zero_tolerance_s_per_lap_per_lap: 1e-9, leave_one_out_refits: [4, 5, 6, 7, 8, 9, 10].map((lap) => ({ omitted_lap_number: lap, slope_s_per_lap_per_lap: 0.05 + lap / 10000, sign: "positive" })), leave_one_out_refit_count: 7, leave_one_out_min_s_per_lap_per_lap: 0.0504, leave_one_out_max_s_per_lap_per_lap: 0.051, sensitivity_envelope: { lower: 0.0504, upper: 0.054, coverage: null, method: "leave-one-observation-out deterministic sensitivity envelope" }, sign_stable: true, sign_counts: { negative: 0, zero: 0, positive: 7 }, maximum_absolute_deviation_s_per_lap_per_lap: 0.0036, most_influential_omitted_lap: 4 },
    unavailable_reason: null, data_quality: quality, provenance: provenance("tyre robustness", null), limitations: ["LOO sensitivity is non-probabilistic."],
  };
}

function unavailableTyre(competitor_id: string) {
  const insufficient = { level: "insufficient", completeness: null, warnings: ["insufficient clean laps: 2 available; 5 required"], missing_fields: [] };
  const diagnostics = { ...fitDiagnostics(competitor_id, tyreModel), candidate_laps: 3, included_laps: 2, excluded_laps: 1, residual_median_s: null, residual_median_absolute_s: null, compound: "soft", stint_number: 2, minimum_tyre_age_laps: 1, maximum_tyre_age_laps: 2, tyre_age_span_laps: 1, intercept_s: null, data_quality: insufficient };
  return { competitor_id, as_of: diagnostics.as_of, point_model_version: tyreModel, robustness_model_version: robustnessModel, point_fit: { competitor_id, estimate: null, diagnostics, selection_audit: selectionAudit, unavailable_reason: "insufficient_clean_laps" }, diagnostics: null, unavailable_reason: "point_estimate_unavailable", data_quality: insufficient, provenance: provenance("tyre robustness", null), limitations: ["No earlier stint fallback"] };
}

const reconstructed = {
  race_state: {
    session: { name: "Race", event: { name: "Monaco Grand Prix" } }, observation_cutoff: "2024-05-26T13:57:58Z",
    track_status: { status: "green", observed_at: "2024-05-26T13:44:00Z", provenance: provenance("race_control", "2024-05-26T13:44:00Z") },
    weather: { observed_at: "2024-05-26T13:56:59Z", air_temperature_c: 22.1, track_temperature_c: 47.4, humidity_fraction: 0.65, wind_speed_mps: 0.7, rainfall_detected: false },
    competitors: [car(16, "Charles Leclerc", 1), car(4, "Lando Norris", 2)], data_quality: quality, provenance: [],
  },
  reconstruction_diagnostics: { bounded_pit_lane_passages: 16, cache_hits: {} },
  modelling_diagnostics: { source_lap_rows: 20, admitted_observations: 18, admission_rejections: {}, rows_bounded_out: 2, foreign_session_rows: 0, unmapped_competitor_rows: 0, exact_duplicate_laps: 0, conflicting_laps: 0, future_stint_starts: 0, ambiguous_stint_annotations: 0, tyre_annotations: 18, weather_alignments: 18, race_control_alignments: 18, gap_alignments: 18, pit_lane_affected_observations: 1, feed_cache_hits: {} },
  pace: { as_of: "2024-05-26T13:57:58Z", point_model_version: paceModel, robustness_model_version: robustnessModel, competitors: [paceResult("competitor:16", 79.419), paceResult("competitor:4", 80.2)] },
  tyre_age_slope: { as_of: "2024-05-26T13:57:58Z", point_model_version: tyreModel, robustness_model_version: robustnessModel, competitors: [availableTyre("competitor:16"), unavailableTyre("competitor:4")] },
  evidence: [
    { competitor_id: "competitor:16", pace: { candidate_laps: [3, 4, 5, 6, 7, 8, 9, 10], included_laps: [4, 5, 6, 7, 8, 9, 10], excluded_laps: [{ lap_number: 3, reasons: ["pit_out"] }] }, tyre_age_slope: { candidate_laps: [3, 4, 5, 6, 7, 8, 9, 10], included_laps: [4, 5, 6, 7, 8, 9, 10], excluded_laps: [{ lap_number: 3, reasons: ["pit_out"] }] } },
    { competitor_id: "competitor:4", pace: { candidate_laps: [2, 3, 4, 5, 6, 7, 8, 9], included_laps: [3, 4, 5, 6, 7, 8, 9], excluded_laps: [{ lap_number: 2, reasons: ["pit_out"] }] }, tyre_age_slope: { candidate_laps: [7, 8, 9], included_laps: [8, 9], excluded_laps: [{ lap_number: 7, reasons: ["pit_out"] }] } },
  ],
};

async function mockWorkbench(page: Page, failAnalysis = false, slowAnalysis = false) {
  await page.route("**/v2/historical/sessions?year=**", (route) => {
    const year = new URL(route.request().url()).searchParams.get("year");
    return route.fulfill({ json: year === "2024" ? [session] : [] });
  });
  await page.route("**/v2/historical/sessions/9523/drivers", (route) => route.fulfill({ json: drivers }));
  await page.route("**/v2/historical/sessions/9523/drivers/*/decision-laps", (route) => route.fulfill({ json: { session_key: 9523, driver_number: 4, laps: [9, 10] } }));
  await page.route("**/v2/historical/analysis", async (route) => {
    if (slowAnalysis) await new Promise((resolve) => setTimeout(resolve, 200));
    if (failAnalysis) return route.fulfill({ status: 502, json: { detail: "Historical data provider is temporarily unavailable." } });
    return route.fulfill({ json: reconstructed });
  });
}

test("historical model workflow exposes pace, tyre robustness, evidence, and synchronized selection", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockWorkbench(page);
  await page.goto("/workbench");
  await expect(page.getByLabel("Event")).toHaveValue("9523");
  await page.getByLabel("Focal driver").selectOption("16");
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
  await page.getByRole("button", { name: "Analyze decision point" }).click();
  await expect(page.getByTestId("model-summary").getByRole("heading", { name: "Charles Leclerc" })).toBeVisible();
  await expect(page.getByLabel("Representative pace analysis")).toContainText("79.419 s/lap");
  await expect(page.getByLabel("Representative pace analysis")).toContainText("78.319");
  await expect(page.getByLabel("Representative pace analysis")).toContainText("80.719");
  await expect(page.getByLabel("Tyre-age pace slope analysis")).toContainText("+0.054 s/lap/lap");
  await expect(page.getByLabel("Tyre-age pace slope analysis")).toContainText("SIGN STABLE");
  await expect(page.getByTestId("model-field-table")).toBeVisible();
  await page.getByTestId("model-field-table").getByRole("button", { name: "Lando Norris" }).click();
  await expect(page.getByTestId("model-summary").getByRole("heading", { name: "Lando Norris" })).toBeVisible();
  await expect(page.getByLabel("Tyre-age pace slope analysis")).toContainText("Insufficient clean laps in latest stint");
  await expect(page.getByLabel("Tyre-age pace slope analysis")).toContainText("No earlier stint substituted");
  await page.getByText("Pace evidence & diagnostics").click();
  await expect(page.getByTestId("model-diagnostics")).toContainText("Included laps");
  await expect(page.getByTestId("model-diagnostics")).toContainText(paceModel.config_hash);
});

test("direct navigation and hard refresh preserve the historical model route", async ({ page }) => {
  await mockWorkbench(page);
  await page.goto("/workbench");
  await expect(page.getByRole("heading", { name: "Historical Model Workbench" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Historical Model Workbench" })).toBeVisible();
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
});

test("analysis loading and sanitized provider failure retain selections", async ({ page }) => {
  await mockWorkbench(page, true, true);
  await page.goto("/workbench");
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
  await page.getByRole("button", { name: "Analyze decision point" }).click();
  await expect(page.getByText("Reconstructing bounded race state and model evidence…")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("Historical data provider is temporarily unavailable.");
  await expect(page.getByLabel("Event")).toHaveValue("9523");
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
});

test("changing season resets incompatible workbench selections", async ({ page }) => {
  await mockWorkbench(page);
  await page.goto("/workbench");
  await page.getByLabel("Season").selectOption("2023");
  await expect(page.getByRole("alert")).toContainText("No historical Grand Prix race sessions");
  await expect(page.getByLabel("Event")).toBeDisabled();
  await expect(page.getByLabel("Focal driver")).toBeDisabled();
});

test("malformed discovery and analysis responses fail without fabricated model state", async ({ page }) => {
  await page.route("**/v2/historical/sessions?year=**", (route) => route.fulfill({ json: [{ ...session, session_key: "9523" }] }));
  await page.goto("/workbench");
  await expect(page.getByRole("alert")).toContainText("malformed session data");
  await expect(page.getByTestId("model-summary")).toHaveCount(0);

  await page.unroute("**/v2/historical/sessions?year=**");
  await mockWorkbench(page);
  await page.unroute("**/v2/historical/analysis");
  await page.route("**/v2/historical/analysis", (route) => route.fulfill({ json: { ...reconstructed, pace: { ...reconstructed.pace, as_of: "2099-01-01T00:00:00Z" } } }));
  await page.reload();
  await expect(page.getByLabel("Decision lap")).toHaveValue("10");
  await page.getByRole("button", { name: "Analyze decision point" }).click();
  await expect(page.getByRole("alert")).toContainText("inconsistent historical analysis data");
  await expect(page.getByTestId("model-summary")).toHaveCount(0);
});

test("desktop controls form one aligned operator row", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockWorkbench(page);
  await page.goto("/workbench");
  const controls = await Promise.all([
    page.getByLabel("Season").boundingBox(), page.getByLabel("Event").boundingBox(),
    page.getByLabel("Session context").boundingBox(), page.getByLabel("Focal driver").boundingBox(),
    page.getByLabel("Decision lap").boundingBox(), page.getByRole("button", { name: "Analyze decision point" }).boundingBox(),
  ]);
  const tops = controls.map((box) => box?.y ?? -100);
  expect(Math.max(...tops) - Math.min(...tops)).toBeLessThan(24);
});

test("mobile summary is readable without page-level horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockWorkbench(page);
  await page.goto("/workbench");
  await page.getByRole("button", { name: "Analyze decision point" }).click();
  await expect(page.getByTestId("model-summary")).toBeVisible();
  await expect(page.getByTestId("model-field-table")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
