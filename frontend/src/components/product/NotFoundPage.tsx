import ProductHeader from "./ProductHeader";

export default function NotFoundPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <ProductHeader current={null} title="Route not found" meta="The requested RaceBrain product surface does not exist" />
      <section className="mx-auto max-w-2xl px-4 py-20 text-center">
        <p className="font-mono text-sm text-cyan-400">404 / UNKNOWN ROUTE</p>
        <h2 className="mt-4 text-2xl font-semibold">No product surface exists at this path.</h2>
        <p className="mt-3 text-sm text-slate-400">Return to RaceBrain or open one of the supported operator tools.</p>
        <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row"><a href="/" className="bg-cyan-500 px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-950">Product entrance</a><a href="/workbench" className="border border-slate-600 px-5 py-3 text-xs font-bold uppercase tracking-wider">Historical workbench</a></div>
      </section>
    </main>
  );
}
