import type { LiveStrategyResponse } from "../../types/raceData";

export default function RaceStateSummary({
  data,
}: {
  data: LiveStrategyResponse;
}) {
  const { weather, race_control, driver_lap_summary } =
    data.race_state_summary;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <p className="text-sm uppercase tracking-[0.2em] text-white/40">
        Race State Summary
      </p>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <Metric label="Track Temp" value={`${weather.track_temperature_avg}°C`} />
        <Metric label="Air Temp" value={`${weather.air_temperature_avg}°C`} />
        <Metric label="Safety Cars" value={String(race_control.safety_car_events)} />
        <Metric label="Red Flags" value={String(race_control.red_flag_events)} />
        <Metric label="Avg Lap" value={`${driver_lap_summary.average_lap_time}s`} />
        <Metric label="Best Lap" value={`${driver_lap_summary.best_lap_time}s`} />
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-black/30 p-3">
        <p className="text-xs uppercase tracking-[0.2em] text-white/40">
          Notable Events
        </p>

        <ul className="mt-2 space-y-1 text-sm text-white/60">
          {race_control.notable_events.slice(0, 5).map((event, index) => (
            <li key={index}>• {event}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-black/30 p-3">
      <p className="text-xs uppercase tracking-[0.2em] text-white/40">
        {label}
      </p>
      <p className="mt-1 text-lg font-black text-white">{value}</p>
    </div>
  );
}