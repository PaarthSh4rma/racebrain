type ProductRoute = "home" | "workbench" | "simulation";

const links: { route: ProductRoute; href: string; label: string }[] = [
  { route: "home", href: "/", label: "RaceBrain" },
  { route: "workbench", href: "/workbench", label: "Workbench" },
  { route: "simulation", href: "/simulation", label: "Simulation Lab" },
];

export default function ProductHeader({ current, title, meta }: {
  current: ProductRoute | null;
  title: string;
  meta: string;
}) {
  return (
    <header className="border-b border-slate-700 bg-slate-900">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-cyan-400">Race Strategy Decision Support</p>
          <h1 className="mt-1 truncate text-lg font-semibold text-slate-100">{title}</h1>
          <p className="mt-1 text-xs text-slate-500">{meta}</p>
        </div>
        <nav aria-label="Product navigation" className="flex max-w-full overflow-x-auto border border-slate-700 bg-slate-950 p-1">
          {links.map((link) => (
            <a
              key={link.route}
              href={link.href}
              aria-current={current === link.route ? "page" : undefined}
              className={`whitespace-nowrap px-3 py-2 text-[11px] font-semibold uppercase tracking-wider ${current === link.route ? "bg-cyan-500 text-slate-950" : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"}`}
            >
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
