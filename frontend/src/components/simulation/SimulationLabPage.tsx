import { useEffect, useMemo, useState } from "react";
import { getTrackProfiles, runMonteCarloSimulation, SCENARIO_SIMULATION_CONFIG } from "../../api/racebrain";
import type { SimulationInputs, SimulationResult, TrackProfile } from "../../types/racebrain";
import ProductHeader from "../product/ProductHeader";
import SimulationResults from "./SimulationResults";

const initialInputs: SimulationInputs = {
  total_laps: 20,
  base_lap_time: 90,
  pit_loss: 22,
  simulations: 200,
  seed: null,
};

function RangeControl({ label, value, min, max, step, suffix = "", onChange }: {
  label: string; value: number; min: number; max: number; step: number; suffix?: string; onChange: (value: number) => void;
}) {
  return <label className="block border border-slate-700 bg-slate-950 p-3 text-xs text-slate-400"><span className="flex items-center justify-between gap-3"><span>{label}</span><span className="font-mono text-sm text-slate-100">{value}{suffix}</span></span><input aria-label={label} className="mt-3 w-full accent-cyan-500" type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

export default function SimulationLabPage() {
  const [tracks, setTracks] = useState<TrackProfile[]>([]);
  const [trackId, setTrackId] = useState("monaco");
  const [inputs, setInputs] = useState<SimulationInputs>(initialInputs);
  const [loadingTracks, setLoadingTracks] = useState(true);
  const [running, setRunning] = useState(false);
  const [trackError, setTrackError] = useState<string | null>(null);
  const [simulationError, setSimulationError] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const selectedTrack = useMemo(() => tracks.find((track) => track.id === trackId), [tracks, trackId]);

  useEffect(() => {
    const controller = new AbortController();
    void getTrackProfiles(controller.signal).then((profiles) => {
      if (!profiles.length) throw new Error("No supported track profiles are currently available.");
      setTracks(profiles);
      const initial = profiles.find((profile) => profile.id === "monaco") ?? profiles[0];
      setTrackId(initial.id);
      setInputs((current) => ({ ...current, base_lap_time: initial.base_lap_time, pit_loss: initial.pit_loss }));
    }).catch((error) => { if (!(error instanceof Error && error.name === "AbortError")) setTrackError(error instanceof Error ? error.message : "Failed to load track profiles."); }).finally(() => { if (!controller.signal.aborted) setLoadingTracks(false); });
    return () => controller.abort();
  }, []);

  function chooseTrack(nextId: string) {
    const profile = tracks.find((item) => item.id === nextId);
    setTrackId(nextId); setResult(null); setSimulationError(null);
    if (profile) setInputs((current) => ({ ...current, base_lap_time: profile.base_lap_time, pit_loss: profile.pit_loss }));
  }

  async function run() {
    setRunning(true); setSimulationError(null); setResult(null);
    try { setResult(await runMonteCarloSimulation(trackId, inputs)); }
    catch (error) { setSimulationError(error instanceof Error ? error.message : "Failed to run simulation."); }
    finally { setRunning(false); }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100" data-testid="simulation-lab">
      <ProductHeader current="simulation" title="Scenario Simulation Lab" meta="Stochastic strategy exploration · experimental" />
      <div className="mx-auto max-w-[1400px] space-y-4 p-3 sm:p-4">
        <section className="grid gap-4 border border-slate-700 bg-slate-900 p-4 lg:grid-cols-[1fr_auto] lg:items-end">
          <div><div className="flex flex-wrap items-center gap-2"><span className="border border-amber-700 bg-amber-950/30 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-amber-300">Experimental</span><span className="text-xs text-slate-500">Separate from the deterministic historical V2 modelling path</span></div><h2 className="mt-3 text-2xl font-semibold">Explore generated strategy candidates under sampled race-time conditions.</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">Candidates are deterministically pre-ranked, then compared with Monte Carlo lap-time, pit-loss, degradation and safety-car perturbations. Results describe this candidate set—not real-race win probability.</p></div>
          <a href="/workbench" className="border border-slate-600 px-4 py-3 text-center text-xs font-bold uppercase tracking-wider text-slate-300 hover:border-cyan-500 hover:text-cyan-300">Open historical workbench</a>
        </section>

        <section className="border border-slate-700 bg-slate-900" aria-labelledby="simulation-controls-heading">
          <header className="border-b border-slate-700 px-4 py-3"><h2 id="simulation-controls-heading" className="text-sm font-semibold uppercase tracking-[0.16em]">Simulation controls</h2><p className="mt-1 text-xs text-slate-500">Adjust bounded scenario inputs before generating and sampling strategy candidates.</p></header>
          <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-6">
            <label className="block border border-slate-700 bg-slate-950 p-3 text-xs text-slate-400">Circuit<select aria-label="Circuit" value={trackId} onChange={(event) => chooseTrack(event.target.value)} disabled={loadingTracks || !tracks.length} className="mt-2 w-full bg-slate-950 py-2 text-sm font-medium text-slate-100 outline-none disabled:text-slate-600">{tracks.map((track) => <option key={track.id} value={track.id}>{track.name}</option>)}</select></label>
            <RangeControl label="Total laps" value={inputs.total_laps} min={16} max={100} step={1} onChange={(value) => setInputs({ ...inputs, total_laps: value })} />
            <RangeControl label="Base lap time" value={inputs.base_lap_time} min={60} max={130} step={0.5} suffix=" s" onChange={(value) => setInputs({ ...inputs, base_lap_time: value })} />
            <RangeControl label="Pit loss" value={inputs.pit_loss} min={15} max={35} step={0.5} suffix=" s" onChange={(value) => setInputs({ ...inputs, pit_loss: value })} />
            <RangeControl label="Runs per strategy" value={inputs.simulations} min={50} max={200} step={50} onChange={(value) => setInputs({ ...inputs, simulations: value })} />
            <label className="block border border-slate-700 bg-slate-950 p-3 text-xs text-slate-400">Simulation seed <span className="text-slate-600">(optional)</span><input aria-label="Simulation seed" type="number" inputMode="numeric" step="1" value={inputs.seed ?? ""} onChange={(event) => { const value = Number(event.target.value); setInputs({ ...inputs, seed: event.target.value === "" || !Number.isSafeInteger(value) ? null : value }); }} placeholder="Random" className="mt-2 w-full bg-slate-950 py-2 font-mono text-sm text-slate-100 outline-none placeholder:text-slate-600" /></label>
          </div>
          <div className="flex flex-wrap items-center gap-3 border-t border-slate-700 px-4 py-3"><button onClick={() => void run()} disabled={running || loadingTracks || !selectedTrack} className="min-h-[42px] bg-cyan-500 px-5 text-xs font-bold uppercase tracking-wider text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400">{running ? "Sampling scenarios…" : "Run scenario simulation"}</button><p className="text-xs text-slate-500">One-stop and two-stop generation · maximum {SCENARIO_SIMULATION_CONFIG.maximumEvaluatedCandidates} evaluated candidates</p></div>
          {trackError && <div role="alert" className="border-t border-amber-800 bg-amber-950/20 px-4 py-3 text-sm text-amber-200">Track profiles could not be loaded. {trackError}</div>}
          {simulationError && <div role="alert" className="border-t border-amber-800 bg-amber-950/20 px-4 py-3 text-sm text-amber-200">Simulation failed safely. {simulationError}</div>}
        </section>

        {running && <section role="status" className="border border-slate-700 bg-slate-900 py-14 text-center"><p className="text-sm font-semibold">Generating candidates and sampling paired race scenarios…</p><p className="mt-2 text-xs text-slate-500">The backend may take longer to respond after an idle deployment.</p></section>}
        {!running && !result && !simulationError && <section className="border border-dashed border-slate-700 py-14 text-center"><h2 className="text-sm font-semibold">No scenario comparison loaded</h2><p className="mt-2 text-sm text-slate-500">Configure the lab and run a bounded Monte Carlo comparison.</p></section>}
        {result && <SimulationResults result={result} inputs={inputs} />}
      </div>
    </main>
  );
}
