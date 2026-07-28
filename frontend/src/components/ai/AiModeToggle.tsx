export default function AiModeToggle({
  useLlm,
  onToggle,
}: {
  useLlm: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm font-black text-white">LLM Mode</p>
        <p className="text-sm text-white/50">
          Uses grounded OpenRouter responses instead of deterministic analysis only.
        </p>
      </div>

      <button
        onClick={onToggle}
        className={`self-start rounded-full px-4 py-2 text-sm font-black transition sm:self-auto ${
          useLlm ? "bg-cyan-500 text-black" : "bg-white/10 text-white/60"
        }`}
      >
        {useLlm ? "ON" : "OFF"}
      </button>
    </div>
  );
}
