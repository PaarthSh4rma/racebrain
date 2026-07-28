import { useRef, useState } from "react";

import {
  getDecisionLaps,
  getHistoricalSessions,
  getReplayAssessment,
  getSessionDrivers,
} from "../../api/raceData";
import type {
  DriverSummary,
  HistoricalSession,
  ReplayAssessment,
} from "../../types/raceData";
import ReplayAssessmentView from "./ReplayAssessmentView";

export default function ReplayPanel() {
  const [year, setYear] = useState(2024);
  const [countryName, setCountryName] = useState("Monaco");
  const [sessions, setSessions] = useState<HistoricalSession[]>([]);
  const [drivers, setDrivers] = useState<DriverSummary[]>([]);
  const [decisionLaps, setDecisionLaps] = useState<number[]>([]);
  const [sessionKey, setSessionKey] = useState<number | null>(null);
  const [driverNumber, setDriverNumber] = useState<number | null>(null);
  const [decisionLap, setDecisionLap] = useState<number | null>(null);
  const [assessment, setAssessment] = useState<ReplayAssessment | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [loadedSession, setLoadedSession] = useState(false);
  const [loadedDriver, setLoadedDriver] = useState(false);
  const requestVersion = useRef(0);

  function beginRequest() {
    requestVersion.current += 1;
    setLoading(true);
    return requestVersion.current;
  }

  async function searchSessions() {
    const version = beginRequest();
    setError(null);
    setAssessment(null);
    setSearched(false);
    setLoadedSession(false);
    setLoadedDriver(false);
    setSessions([]);
    setDrivers([]);
    setDecisionLaps([]);
    setSessionKey(null);
    setDriverNumber(null);
    setDecisionLap(null);
    try {
      const result = await getHistoricalSessions({ year, countryName });
      if (version !== requestVersion.current) return;
      setSessions(result);
      setDrivers([]);
      setDecisionLaps([]);
      setSessionKey(null);
      setDriverNumber(null);
      setDecisionLap(null);
      setSearched(true);
    } catch (caught) {
      if (version !== requestVersion.current) return;
      setError(caught instanceof Error ? caught.message : "Session search failed.");
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }

  async function selectSession(value: number) {
    const version = beginRequest();
    setSessionKey(value);
    setDrivers([]);
    setDriverNumber(null);
    setDecisionLap(null);
    setDecisionLaps([]);
    setAssessment(null);
    setError(null);
    setLoadedSession(false);
    setLoadedDriver(false);
    try {
      const result = await getSessionDrivers(value);
      if (version !== requestVersion.current) return;
      setDrivers(result);
      setLoadedSession(true);
    } catch (caught) {
      if (version !== requestVersion.current) return;
      setError(caught instanceof Error ? caught.message : "Driver loading failed.");
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }

  async function selectDriver(value: number) {
    if (sessionKey === null) return;
    const version = beginRequest();
    setDriverNumber(value);
    setDecisionLaps([]);
    setDecisionLap(null);
    setAssessment(null);
    setError(null);
    setLoadedDriver(false);
    try {
      const laps = await getDecisionLaps(sessionKey, value);
      if (version !== requestVersion.current) return;
      setDecisionLaps(laps);
      setDecisionLap(laps.at(-1) ?? null);
      setLoadedDriver(true);
    } catch (caught) {
      if (version !== requestVersion.current) return;
      setError(caught instanceof Error ? caught.message : "Decision laps failed to load.");
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }

  async function loadReplay() {
    if (sessionKey === null || driverNumber === null || decisionLap === null) return;
    const version = beginRequest();
    setError(null);
    setAssessment(null);
    try {
      const result = await getReplayAssessment({
        sessionKey,
        driverNumber,
        decisionLap,
      });
      if (version !== requestVersion.current) return;
      setAssessment(result);
    } catch (caught) {
      if (version !== requestVersion.current) return;
      setError(caught instanceof Error ? caught.message : "Replay reconstruction failed.");
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }

  return (
    <section
      data-testid="historical-card"
      className="mt-6 min-w-0 rounded-[2rem] border border-white/10 bg-black/40 p-4 backdrop-blur-xl sm:mt-8 sm:p-6"
    >
      <header className="mb-6">
        <p className="text-xs uppercase tracking-[0.3em] text-red-400">
          Historical Decision Replay
        </p>
        <h2 className="mt-2 break-words text-2xl font-black sm:text-3xl">
          Reconstruct the call without hindsight.
        </h2>
        <p className="mt-3 max-w-3xl text-white/50">
          Choose a completed lap and rebuild only the weather, stint, pace, and
          race-control evidence knowable at that moment.
        </p>
      </header>

      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div className="min-w-0 space-y-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm font-black uppercase tracking-[0.18em] text-white/50">
              1. Find a race
            </p>
            <div className="mt-3 grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-[120px_1fr_auto]">
              <input
                aria-label="Replay year"
                type="number"
                value={year}
                disabled={loading}
                onChange={(event) => setYear(Number(event.target.value))}
                className="min-w-0 rounded-xl border border-white/10 bg-black/40 px-4 py-3"
              />
              <input
                aria-label="Replay country"
                value={countryName}
                disabled={loading}
                onChange={(event) => setCountryName(event.target.value)}
                className="min-w-0 rounded-xl border border-white/10 bg-black/40 px-4 py-3"
              />
              <button
                onClick={() => void searchSessions()}
                disabled={loading}
                className="rounded-xl bg-red-600 px-5 py-3 font-black disabled:opacity-50"
              >
                Search
              </button>
            </div>
          </div>

          {sessions.length > 0 && (
            <label className="block rounded-2xl border border-white/10 bg-white/5 p-4">
              <span className="text-sm font-black uppercase tracking-[0.18em] text-white/50">
                2. Select session
              </span>
              <select
                aria-label="Historical session"
                value={sessionKey ?? ""}
                disabled={loading}
                onChange={(event) => void selectSession(Number(event.target.value))}
                className="mt-3 w-full min-w-0 rounded-xl border border-white/10 bg-black px-4 py-3"
              >
                <option value="" disabled>Choose a race</option>
                {sessions.map((session) => (
                  <option key={session.session_key} value={session.session_key}>
                    {session.year} {session.country_name} — {session.session_name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {searched && sessions.length === 0 && !error && (
            <p role="status" className="rounded-xl bg-white/5 p-4 text-sm text-white/60">
              No historical race sessions matched that search.
            </p>
          )}

          {drivers.length > 0 && (
            <label className="block rounded-2xl border border-white/10 bg-white/5 p-4">
              <span className="text-sm font-black uppercase tracking-[0.18em] text-white/50">
                3. Select driver
              </span>
              <select
                aria-label="Replay driver"
                value={driverNumber ?? ""}
                disabled={loading}
                onChange={(event) => void selectDriver(Number(event.target.value))}
                className="mt-3 w-full min-w-0 rounded-xl border border-white/10 bg-black px-4 py-3"
              >
                <option value="" disabled>Choose a driver</option>
                {drivers.map((driver) => (
                  <option key={driver.driver_number} value={driver.driver_number}>
                    {driver.name_acronym ?? driver.full_name} #{driver.driver_number}
                  </option>
                ))}
              </select>
            </label>
          )}
          {loadedSession && drivers.length === 0 && !error && (
            <p role="status" className="rounded-xl bg-white/5 p-4 text-sm text-white/60">
              No driver records are available for this session.
            </p>
          )}

          {decisionLaps.length > 0 && (
            <label className="block rounded-2xl border border-white/10 bg-white/5 p-4">
              <span className="text-sm font-black uppercase tracking-[0.18em] text-white/50">
                4. Decision lap
              </span>
              <select
                aria-label="Decision lap"
                value={decisionLap ?? ""}
                disabled={loading}
                onChange={(event) => {
                  requestVersion.current += 1;
                  setLoading(false);
                  setDecisionLap(Number(event.target.value));
                  setAssessment(null);
                }}
                className="mt-3 w-full rounded-xl border border-white/10 bg-black px-4 py-3"
              >
                {decisionLaps.map((lap) => (
                  <option key={lap} value={lap}>Completed lap {lap}</option>
                ))}
              </select>
            </label>
          )}
          {loadedDriver && decisionLaps.length === 0 && !error && (
            <p role="status" className="rounded-xl bg-white/5 p-4 text-sm text-white/60">
              No completed decision laps are available for this driver.
            </p>
          )}

          <button
            onClick={() => void loadReplay()}
            disabled={
              loading ||
              sessionKey === null ||
              driverNumber === null ||
              decisionLap === null
            }
            className="w-full rounded-2xl bg-red-600 px-4 py-4 text-sm font-black uppercase tracking-[0.15em] disabled:opacity-50"
          >
            {loading ? "Reconstructing race state..." : "Load Decision Replay"}
          </button>

          {error && (
            <p
              role="alert"
              className="break-words rounded-2xl border border-red-500/25 bg-red-500/5 p-4 text-sm text-red-200"
            >
              {error}
            </p>
          )}
        </div>

        <div className="min-w-0">
          {assessment ? (
            <ReplayAssessmentView assessment={assessment} />
          ) : (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-white/50">
              Complete the guided steps to inspect the reconstructed race state,
              deterministic recommendation, and alternative calls.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
