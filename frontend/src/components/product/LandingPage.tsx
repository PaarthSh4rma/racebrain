import ProductHeader from "./ProductHeader";

const capabilities = [
  ["Historical RaceState", "OPERATIONAL"],
  ["Representative Pace", "OPERATIONAL"],
  ["Empirical Pace Spread", "OPERATIONAL"],
  ["Tyre-Age Pace Slope", "OPERATIONAL"],
  ["LOO Robustness", "OPERATIONAL"],
  ["Competitors & Traffic", "NEXT"],
  ["Strategy Decision Engine", "PLANNED"],
] as const;

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100" data-testid="product-entrance">
      <ProductHeader current="home" title="RaceBrain" meta="Public product entrance · V2 modelling and simulation surfaces" />
      <div className="mx-auto grid max-w-[1320px] gap-6 px-4 py-8 lg:grid-cols-[1.15fr_0.85fr] lg:py-14">
        <section className="border border-slate-700 bg-slate-900 p-6 sm:p-8" aria-labelledby="product-heading">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-400">RaceBrain</p>
          <h2 id="product-heading" className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight sm:text-5xl">Race Strategy Decision Support</h2>
          <div className="mt-6 max-w-2xl space-y-2 border-l-2 border-cyan-600 pl-4 text-base leading-7 text-slate-300">
            <p>Reconstruct race state.</p>
            <p>Model pace and tyre behaviour.</p>
            <p>Inspect evidence and robustness.</p>
            <p>Explore stochastic strategy scenarios.</p>
          </div>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <a href="/workbench" className="bg-cyan-500 px-5 py-3 text-center text-xs font-bold uppercase tracking-wider text-slate-950 hover:bg-cyan-300">Open Historical Workbench</a>
            <a href="/simulation" className="border border-slate-600 px-5 py-3 text-center text-xs font-bold uppercase tracking-wider text-slate-200 hover:border-cyan-500 hover:text-cyan-300">Open Scenario Simulation Lab</a>
          </div>
        </section>

        <section className="border border-slate-700 bg-slate-900" aria-labelledby="system-heading">
          <header className="border-b border-slate-700 px-4 py-3"><p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Current system</p><h2 id="system-heading" className="mt-1 text-sm font-semibold uppercase tracking-wider">Capability status</h2></header>
          <dl>{capabilities.map(([name, status]) => <div key={name} className="grid grid-cols-[1fr_auto] gap-4 border-b border-slate-800 px-4 py-3 last:border-b-0"><dt className="text-sm text-slate-300">{name}</dt><dd className={`font-mono text-xs font-semibold ${status === "OPERATIONAL" ? "text-emerald-400" : status === "NEXT" ? "text-cyan-300" : "text-slate-500"}`}>{status}</dd></div>)}</dl>
        </section>

        <section className="grid gap-px border border-slate-700 bg-slate-700 lg:col-span-2 md:grid-cols-2" aria-label="RaceBrain modelling approaches">
          <article className="bg-slate-900 p-5"><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-400">Primary product</p><h2 className="mt-2 text-xl font-semibold">Historical Model Workbench</h2><p className="mt-3 text-sm leading-6 text-slate-400">Deterministic, cutoff-safe reconstruction from real historical evidence with no-hindsight boundaries, DataQuality, provenance, model evidence and robustness.</p></article>
          <article className="bg-slate-900 p-5"><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-300">Experimental lab</p><h2 className="mt-2 text-xl font-semibold">Scenario Simulation Lab</h2><p className="mt-3 text-sm leading-6 text-slate-400">Generated strategy candidates, deterministic pre-ranking and Monte Carlo race-time perturbations for exploratory scenario comparison—not the V2 historical decision engine.</p></article>
        </section>
        <p className="text-xs leading-5 text-slate-500 lg:col-span-2">Historical replay and validation are handled through the model workbench. Scenario exploration remains a separate experimental surface.</p>
      </div>
    </main>
  );
}
