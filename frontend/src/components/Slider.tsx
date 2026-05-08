export default function Slider({
  label,
  value,
  min,
  max,
  step,
  suffix = "",
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix?: string;
  onChange: (v: number) => void;
}) {
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className="rounded-2xl border border-white/10 bg-black/40 p-4">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs uppercase tracking-[0.2em] text-white/40">
          {label}
        </p>

        <p className="rounded-full bg-red-500/10 px-3 py-1 text-sm font-black text-red-300">
          {value}
          {suffix}
        </p>
      </div>

      <div className="relative">
        <div className="absolute left-0 top-1/2 h-2 w-full -translate-y-1/2 rounded-full bg-white/10" />

        <div
          className="absolute left-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-red-500"
          style={{ width: `${percentage}%` }}
        />

        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="relative z-10 w-full cursor-pointer appearance-none bg-transparent accent-red-500"
        />
      </div>
    </div>
  );
}