export default function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-0 rounded-2xl border border-white/10 bg-black/40 p-4">
      <div className="mb-3 text-red-400">{icon}</div>
      <p className="break-words text-xs uppercase tracking-[0.15em] text-white/40 sm:tracking-[0.2em]">
        {label}
      </p>
      <p className="mt-2 text-lg font-black">{value}</p>
    </div>
  );
}
