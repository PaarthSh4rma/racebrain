import { useEffect, useMemo, useRef, useState } from "react";
import { getDecisionLaps, getHistoricalDrivers, getHistoricalSessions, reconstructHistoricalState } from "../../api/historical";
import type { CarState, HistoricalDriver, HistoricalRaceStateResponse, HistoricalSession } from "../../types/historical";
import CarDetail from "./CarDetail";
import FieldTable from "./FieldTable";
import { formatNumber, formatUtc, missing } from "./format";

const currentYear = new Date().getUTCFullYear();
const seasons = Array.from({ length: currentYear - 2017 }, (_, index) => currentYear - index);

function message(error: unknown, fallback: string) {
  return error instanceof Error && error.name !== "AbortError" ? error.message : error instanceof Error ? "" : fallback;
}

export default function WorkbenchPage() {
  const [year, setYear] = useState(2024);
  const [sessions, setSessions] = useState<HistoricalSession[]>([]);
  const [sessionKey, setSessionKey] = useState<number | null>(null);
  const [drivers, setDrivers] = useState<HistoricalDriver[]>([]);
  const [driverNumber, setDriverNumber] = useState<number | null>(null);
  const [laps, setLaps] = useState<number[]>([]);
  const [decisionLap, setDecisionLap] = useState<number | null>(null);
  const [result, setResult] = useState<HistoricalRaceStateResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string>();
  const [loading, setLoading] = useState<"sessions" | "drivers" | "laps" | "state" | null>("sessions");
  const [error, setError] = useState<string | null>(null);
  const stateRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getHistoricalSessions(year, controller.signal).then((items) => {
      setSessions(items);
      if (items.length) { setLoading("drivers"); setSessionKey(items[0].session_key); }
      else { setLoading(null); setError("No historical Grand Prix race sessions were found for this season."); }
    }).catch((reason) => { const text = message(reason, "Unable to load historical sessions."); if (text) { setError(text); setLoading(null); } });
    return () => controller.abort();
  }, [year]);

  useEffect(() => {
    if (sessionKey === null) return;
    const controller = new AbortController();
    getHistoricalDrivers(sessionKey, controller.signal).then((items) => {
      setDrivers(items);
      if (items.length) { setLoading("laps"); setDriverNumber(items[0].driver_number); }
      else { setLoading(null); setError("No defensible driver entries were found for this session."); }
    }).catch((reason) => { const text = message(reason, "Unable to load session drivers."); if (text) { setError(text); setLoading(null); } });
    return () => controller.abort();
  }, [sessionKey]);

  useEffect(() => {
    if (sessionKey === null || driverNumber === null) return;
    const controller = new AbortController();
    getDecisionLaps(sessionKey, driverNumber, controller.signal).then((items) => {
      setLaps(items); setDecisionLap(items.at(-1) ?? null); setLoading(null);
    }).catch((reason) => { const text = message(reason, "Unable to load decision laps."); if (text) { setError(text); setLoading(null); } });
    return () => controller.abort();
  }, [sessionKey, driverNumber]);

  const session = sessions.find((item) => item.session_key === sessionKey);
  const selectedCar = useMemo(() => result?.race_state.competitors.find((car) => car.competitor_id === selectedId) ?? null, [result, selectedId]);

  async function loadState() {
    if (sessionKey === null || driverNumber === null || decisionLap === null) return;
    stateRequest.current?.abort();
    const controller = new AbortController();
    stateRequest.current = controller;
    setLoading("state"); setError(null); setResult(null);
    try {
      const next = await reconstructHistoricalState(sessionKey, driverNumber, decisionLap, controller.signal);
      setResult(next);
      const focal = next.race_state.competitors.find((car) => car.external_ids.some((id) => id.resource_type === "driver_number" && id.value === String(driverNumber)));
      setSelectedId((focal ?? next.race_state.competitors[0])?.competitor_id);
    } catch (reason) {
      const text = message(reason, "Historical race state could not be reconstructed.");
      if (text) setError(text);
    } finally { if (!controller.signal.aborted) setLoading(null); }
  }

  function selectYear(next: number) {
    stateRequest.current?.abort(); setYear(next); setLoading("sessions"); setError(null); setSessions([]); setSessionKey(null); setDrivers([]); setDriverNumber(null); setLaps([]); setDecisionLap(null); setResult(null);
  }

  function selectSession(next: number) {
    stateRequest.current?.abort(); setSessionKey(next); setLoading("drivers"); setError(null); setDrivers([]); setDriverNumber(null); setLaps([]); setDecisionLap(null); setResult(null);
  }

  function selectDriver(next: number) {
    stateRequest.current?.abort(); setDriverNumber(next); setLoading("laps"); setError(null); setLaps([]); setDecisionLap(null); setResult(null);
  }

  const state = result?.race_state;
  const weather = state?.weather;
  const contexts = [
    ["Event", state?.session.event.name ?? session?.event_name], ["Session", state?.session.name ?? session?.session_name],
    ["Decision lap", decisionLap], ["Cutoff", state ? formatUtc(state.observation_cutoff) : null],
    ["Track", state?.track_status?.status.replaceAll("_", " ").toUpperCase()],
    ["Air", weather ? formatNumber(weather.air_temperature_c, "°C") : null], ["Track temp", weather ? formatNumber(weather.track_temperature_c, "°C") : null],
    ["Humidity", weather?.humidity_fraction === null || weather?.humidity_fraction === undefined ? null : `${Math.round(weather.humidity_fraction * 100)}%`],
    ["Rain", weather?.rainfall_detected === null || weather?.rainfall_detected === undefined ? null : weather.rainfall_detected ? "Detected" : "Not detected"],
  ];

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100" data-testid="historical-workbench">
      <header className="border-b border-slate-700 bg-slate-900"><div className="mx-auto flex max-w-[1500px] items-center justify-between px-4 py-3"><div><a href="/" className="text-xs font-bold uppercase tracking-[0.25em] text-cyan-400">RaceBrain</a><h1 className="text-lg font-semibold">Historical State Workbench</h1></div><span className="text-xs text-slate-500">Canonical RaceState · UTC</span></div></header>
      <div className="mx-auto max-w-[1500px] space-y-4 p-4">
        <section className="border border-slate-700 bg-slate-900 p-3" aria-label="Historical state controls">
          <div className="grid gap-3 md:grid-cols-6">
            <label className="text-xs text-slate-400">Season<select aria-label="Season" value={year} onChange={(event) => selectYear(Number(event.target.value))} className="mt-1 w-full border border-slate-600 bg-slate-950 px-2 py-2 text-sm text-white">{seasons.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label className="text-xs text-slate-400 md:col-span-2">Event<select aria-label="Event" value={sessionKey ?? ""} onChange={(event) => selectSession(Number(event.target.value))} disabled={!sessions.length} className="mt-1 w-full border border-slate-600 bg-slate-950 px-2 py-2 text-sm text-white disabled:opacity-50"><option value="">Select event</option>{sessions.map((item) => <option key={item.session_key} value={item.session_key}>{item.event_name} · {item.location}</option>)}</select></label>
            <label className="text-xs text-slate-400">Session<select aria-label="Session" value={session?.session_name ?? ""} disabled className="mt-1 w-full border border-slate-600 bg-slate-950 px-2 py-2 text-sm text-white disabled:opacity-70"><option>{session?.session_name ?? "—"}</option></select></label>
            <label className="text-xs text-slate-400">Focal driver<select aria-label="Focal driver" value={driverNumber ?? ""} onChange={(event) => selectDriver(Number(event.target.value))} disabled={!drivers.length} className="mt-1 w-full border border-slate-600 bg-slate-950 px-2 py-2 text-sm text-white disabled:opacity-50"><option value="">Select driver</option>{drivers.map((driver) => <option key={driver.driver_number} value={driver.driver_number}>#{driver.driver_number} {driver.full_name}</option>)}</select></label>
            <label className="text-xs text-slate-400">Decision lap<select aria-label="Decision lap" value={decisionLap ?? ""} onChange={(event) => { setDecisionLap(Number(event.target.value)); setResult(null); }} disabled={!laps.length} className="mt-1 w-full border border-slate-600 bg-slate-950 px-2 py-2 text-sm text-white disabled:opacity-50"><option value="">Select lap</option>{laps.map((lap) => <option key={lap} value={lap}>{lap}</option>)}</select></label>
          </div>
          <div className="mt-3 flex items-center gap-3"><button onClick={() => void loadState()} disabled={loading !== null || decisionLap === null} className="bg-cyan-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400">{loading === "state" ? "Reconstructing…" : "Load state"}</button>{loading && loading !== "state" && <span role="status" className="text-xs text-slate-400">Loading {loading}… OpenF1 cold starts can take several seconds.</span>}</div>
          {error && <div role="alert" className="mt-3 border-l-2 border-amber-500 bg-amber-950/30 px-3 py-2 text-sm text-amber-100">{error} Check the selection or retry when the upstream service is available.</div>}
        </section>

        <section className="grid grid-cols-2 border border-slate-700 bg-slate-900 sm:grid-cols-3 lg:grid-cols-9" aria-label="Session environment">
          {contexts.map(([label, value]) => <div key={String(label)} className="border-b border-r border-slate-700 px-3 py-2"><p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-1 truncate font-mono text-xs text-slate-100" title={String(value ?? missing)}>{value ?? missing}</p></div>)}
        </section>

        {!state && !error && loading !== "state" && <section className="border border-dashed border-slate-700 py-16 text-center"><h2 className="text-sm font-semibold">No reconstructed state loaded</h2><p className="mt-2 text-sm text-slate-400">Choose a race, focal driver, and completed lap, then load the canonical state.</p></section>}
        {loading === "state" && <section role="status" className="border border-slate-700 bg-slate-900 py-16 text-center"><p className="text-sm font-semibold">Reconstructing the bounded field…</p><p className="mt-2 text-xs text-slate-400">Fetching ten historical datasets and applying the no-hindsight cutoff.</p></section>}
        {state && <>
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]"><FieldTable cars={state.competitors} selectedId={selectedId} onSelect={(car: CarState) => setSelectedId(car.competitor_id)} /><CarDetail car={selectedCar} /></div>
          <section className="border border-slate-700 bg-slate-900 p-4" data-testid="global-quality"><div className="flex flex-wrap items-center gap-3"><h2 className="text-sm font-semibold uppercase tracking-wider">Global data quality</h2><span className="border border-amber-700 px-2 py-1 text-xs font-bold uppercase text-amber-300">{state.data_quality.level}</span><span className="text-xs text-slate-500">{result.diagnostics.bounded_pit_lane_passages} bounded pit-lane passages · no stop count inferred</span></div>{state.data_quality.missing_fields.length > 0 && <p className="mt-3 text-sm text-amber-200">Missing: {state.data_quality.missing_fields.join(", ")}</p>}<ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">{state.data_quality.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></section>
        </>}
      </div>
    </main>
  );
}
