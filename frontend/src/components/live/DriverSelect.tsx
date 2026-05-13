import type { Driver } from "../../types/raceData";

export default function DriverSelect({
  drivers,
  selectedDriver,
  onSelectDriver,
}: {
  drivers: Driver[];
  selectedDriver: number | null;
  onSelectDriver: (driverNumber: number) => void;
}) {
  if (drivers.length === 0) return null;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-sm uppercase tracking-[0.2em] text-white/40">
        Driver
      </p>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {drivers.map((driver) => (
          <button
            key={driver.driver_number}
            onClick={() => onSelectDriver(driver.driver_number)}
            className={`rounded-xl border px-4 py-3 text-left transition ${
              selectedDriver === driver.driver_number
                ? "border-cyan-500/50 bg-cyan-500/10"
                : "border-white/10 bg-black/20 hover:bg-white/5"
            }`}
          >
            <p className="font-black text-white">
              {driver.name_acronym} #{driver.driver_number}
            </p>
            <p className="text-sm text-white/50">{driver.team_name}</p>
          </button>
        ))}
      </div>
    </div>
  );
}