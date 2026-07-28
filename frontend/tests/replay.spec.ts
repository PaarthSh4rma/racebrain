import { expect, test, type Page } from "@playwright/test";

const sessions = [
  {
    session_key: 9523,
    session_name: "Race",
    country_name: "Monaco",
    circuit_short_name: "Monte Carlo",
    year: 2024,
  },
];

const drivers = [
  {
    driver_number: 1,
    full_name: "Mock Driver",
    name_acronym: "MCK",
    team_name: "Fixture Racing",
  },
];

function assessment(decisionLap: number, warning = false) {
  return {
    snapshot: {
      session: sessions[0],
      driver: drivers[0],
      decision_lap: decisionLap,
      available_decision_laps: [5, 6],
      cutoff_timestamp: "2024-05-26T13:10:00Z",
      current_stint: {
        stint_number: 1,
        lap_start: 1,
        lap_end: decisionLap,
        compound: "MEDIUM",
        tyre_age_at_start: 0,
      },
      current_compound: "MEDIUM",
      estimated_tyre_age: decisionLap,
      pace: {
        recent_lap_times: [90.1, 90.2, 90.4, 90.5, 90.7],
        recent_average: 90.38,
        previous_average: 90.0,
        trend_seconds_per_lap: 0.38,
        trend: "degrading",
      },
      weather: {
        air_temperature: 22,
        track_temperature: 34,
        humidity: 60,
        wind_speed: 2,
        rainfall_detected: false,
        trend: "dry",
      },
      race_control: {
        safety_car_active: false,
        red_flag_active: false,
        safety_car_events: 0,
        red_flag_events: 0,
        recent_messages: [],
      },
      bounded_laps: [],
      bounded_stints: [],
      data_quality: {
        cutoff_source: "lap_completion_timestamp",
        latest_included_timestamp: "2024-05-26T13:10:00Z",
        records: {
          laps: { included: decisionLap, ignored_future: 6 },
        },
        warnings: warning ? ["Weather samples were incomplete."] : [],
        cache_hits: {},
      },
    },
    recommendation: {
      recommendation: "pit_window_opening",
      confidence: warning ? "medium" : "high",
      summary: "The pit window is opening as tyre and pace risk increase.",
      tyre_risk: "low",
      reasoning_factors: [
        "Current tyre risk is low.",
        "Recent pace trend is degrading.",
      ],
      evidence: {},
      limitations: [],
    },
    alternatives: [
      {
        alternative: "hold",
        strategy_score: 100,
        delta_to_recommended: 0,
        uncertainty: 0.2,
        tyre_risk: "low",
        explanation: "Keeps the current plan, then stops midway through the shared horizon.",
      },
      {
        alternative: "extend",
        strategy_score: 101.2,
        delta_to_recommended: 1.2,
        uncertainty: 0.3,
        tyre_risk: "medium",
        explanation: "Runs five more laps with bounded tyre-age degradation.",
      },
      {
        alternative: "pit_now",
        strategy_score: 103,
        delta_to_recommended: 3,
        uncertainty: 0.4,
        tyre_risk: "low",
        explanation: "Stops immediately and pays an estimated pit-loss cost.",
      },
    ],
    recommended_alternative: "hold",
    seed: 2026,
    simulations: 120,
  };
}

async function mockReplayApi(
  page: Page,
  options?: { warning?: boolean; failAssessment?: boolean },
) {
  await page.route("**/tracks", (route) =>
    route.fulfill({ json: { tracks: [] } }),
  );
  await page.route("**/replay/sessions?**", (route) => route.fulfill({ json: sessions }));
  await page.route("**/replay/sessions/9523/drivers", (route) =>
    route.fulfill({ json: drivers }),
  );
  await page.route("**/replay/sessions/9523/drivers/1/decision-laps", (route) =>
    route.fulfill({ json: { session_key: 9523, driver_number: 1, laps: [5, 6] } }),
  );
  await page.route("**/replay/assessment", async (route) => {
    if (options?.failAssessment) {
      await route.fulfill({
        status: 502,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Historical race data is temporarily unavailable." }),
      });
      return;
    }
    const payload = route.request().postDataJSON() as { decision_lap: number };
    await route.fulfill({ json: assessment(payload.decision_lap, options?.warning) });
  });
}

async function reachDecisionLap(page: Page) {
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByLabel("Historical session").selectOption("9523");
  await page.getByLabel("Replay driver").selectOption("1");
}

test("session to driver to lap replay renders recommendation and alternatives", async ({
  page,
}) => {
  await mockReplayApi(page);
  await page.goto("/");
  await reachDecisionLap(page);
  await expect(page.getByLabel("Decision lap")).toHaveValue("6");
  await page.getByRole("button", { name: "Load Decision Replay" }).click();
  await expect(page.getByTestId("replay-result")).toBeVisible();
  await expect(page.getByText("pit window opening", { exact: true })).toBeVisible();
  await expect(page.getByText("Compared Alternative Calls")).toBeVisible();

  await page.getByLabel("Decision lap").selectOption("5");
  await page.getByRole("button", { name: "Load Decision Replay" }).click();
  await expect(page.getByTestId("decision-lap-value")).toHaveText("5");
});

test("incomplete data and upstream errors remain controlled", async ({ page }) => {
  await mockReplayApi(page, { warning: true });
  await page.goto("/");
  await reachDecisionLap(page);
  await page.getByRole("button", { name: "Load Decision Replay" }).click();
  await expect(page.getByText("Data completeness warning")).toBeVisible();
  await expect(page.getByText("Weather samples were incomplete.")).toBeVisible();

  await page.unroute("**/replay/assessment");
  await page.route("**/replay/assessment", (route) =>
    route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Historical race data is temporarily unavailable." }),
    }),
  );
  await page.getByRole("button", { name: "Load Decision Replay" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Historical race data is temporarily unavailable.",
  );
});

test("replay flow has no horizontal overflow at 390px", async ({ page }) => {
  await mockReplayApi(page);
  await page.goto("/");
  await reachDecisionLap(page);
  await page.getByRole("button", { name: "Load Decision Replay" }).click();
  await expect(page.getByTestId("replay-result")).toBeVisible();
  const width = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(width).toEqual({ viewport: 390, document: 390 });
});

test("empty session search is explained without exposing stale controls", async ({
  page,
}) => {
  await page.route("**/tracks", (route) =>
    route.fulfill({ json: { tracks: [] } }),
  );
  await page.route("**/replay/sessions?**", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(
    page.getByText("No historical race sessions matched that search."),
  ).toBeVisible();
  await expect(page.getByLabel("Historical session")).toHaveCount(0);
});
