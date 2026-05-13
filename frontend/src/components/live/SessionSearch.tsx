import type { RaceSession } from "../../types/raceData";

export default function SessionSearch({
  year,
  countryName,
  loading,
  sessions,
  selectedSessionKey,
  onYearChange,
  onCountryChange,
  onSearch,
  onSelectSession,
}: {
  year: number;
  countryName: string;
  loading: boolean;
  sessions: RaceSession[];
  selectedSessionKey: number | null;
  onYearChange: (value: number) => void;
  onCountryChange: (value: string) => void;
  onSearch: () => void;
  onSelectSession: (sessionKey: number) => void;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-white/40">
        Real Race Session
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-[120px_1fr_auto]">
        <input
          type="number"
          value={year}
          onChange={(event) => onYearChange(Number(event.target.value))}
          className="rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none"
        />

        <input
          value={countryName}
          onChange={(event) => onCountryChange(event.target.value)}
          placeholder="Monaco"
          className="rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none"
        />

        <button
          onClick={onSearch}
          disabled={loading}
          className="rounded-xl bg-red-600 px-5 py-3 font-black text-white transition hover:bg-red-500 disabled:opacity-50"
        >
          {loading ? "Loading..." : "Load"}
        </button>
      </div>

      {sessions.length > 0 && (
        <div className="mt-4 space-y-2">
          {sessions.map((session) => (
            <button
              key={session.session_key}
              onClick={() => onSelectSession(session.session_key)}
              className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                selectedSessionKey === session.session_key
                  ? "border-red-500/50 bg-red-500/10"
                  : "border-white/10 bg-black/20 hover:bg-white/5"
              }`}
            >
              <p className="font-black text-white">
                {session.year} {session.country_name} GP —{" "}
                {session.session_name}
              </p>
              <p className="mt-1 text-sm text-white/50">
                {session.circuit_short_name} · Session Key{" "}
                {session.session_key}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}