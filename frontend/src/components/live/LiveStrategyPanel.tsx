import { useState } from "react";

import {
  getDrivers,
  getLiveStrategy,
  getSessions,
} from "../../api/raceData";

import type {
  Driver,
  LiveStrategyResponse,
  RaceSession,
} from "../../types/raceData";

import DriverSelect from "./DriverSelect";
import LiveStrategyCallCard from "./LiveStrategyCallCard";
import RaceStateSummary from "./RaceStateSummary";
import SessionSearch from "./SessionSearch";

export default function LiveStrategyPanel() {
  const [year, setYear] = useState(2024);
  const [countryName, setCountryName] = useState("Monaco");
  const [sessions, setSessions] = useState<RaceSession[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [selectedSessionKey, setSelectedSessionKey] = useState<number | null>(
    null
  );
  const [selectedDriver, setSelectedDriver] = useState<number | null>(null);
  const [liveStrategy, setLiveStrategy] =
    useState<LiveStrategyResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSearchSessions() {
    setLoading(true);

    try {
      const data = await getSessions({
        year,
        countryName,
        sessionName: "Race",
      });

      setSessions(data);
      setSelectedSessionKey(data[0]?.session_key ?? null);
      setLiveStrategy(null);

      if (data[0]?.session_key) {
        const driverData = await getDrivers(data[0].session_key);
        setDrivers(driverData);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadStrategy() {
    if (!selectedSessionKey) return;

    setLoading(true);

    try {
      const data = await getLiveStrategy({
        sessionKey: selectedSessionKey,
        driverNumber: selectedDriver,
      });

      setLiveStrategy(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-8 rounded-[2rem] border border-white/10 bg-black/40 p-6 backdrop-blur-xl">
      <div className="mb-6">
        <p className="text-xs uppercase tracking-[0.35em] text-red-400">
          V3 Real Race Intelligence
        </p>

        <h2 className="mt-2 text-3xl font-black">
          OpenF1 Live Strategy Mode
        </h2>

        <p className="mt-3 text-white/50">
          Load real historical race sessions, select a driver, and generate a
          strategy call from OpenF1 race state.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <SessionSearch
            year={year}
            countryName={countryName}
            loading={loading}
            sessions={sessions}
            selectedSessionKey={selectedSessionKey}
            onYearChange={setYear}
            onCountryChange={setCountryName}
            onSearch={handleSearchSessions}
            onSelectSession={setSelectedSessionKey}
          />

          <DriverSelect
            drivers={drivers}
            selectedDriver={selectedDriver}
            onSelectDriver={setSelectedDriver}
          />

          <button
            onClick={handleLoadStrategy}
            disabled={loading || !selectedSessionKey}
            className="w-full rounded-2xl bg-red-600 px-6 py-4 font-black uppercase tracking-[0.2em] text-white transition hover:bg-red-500 disabled:opacity-50"
          >
            {loading ? "Building Race State..." : "Generate Live Strategy Call"}
          </button>
        </div>

        <div className="space-y-4">
          {liveStrategy ? (
            <>
              <LiveStrategyCallCard data={liveStrategy} />
              <RaceStateSummary data={liveStrategy} />
            </>
          ) : (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-white/50">
              Load a race session and driver to generate real race intelligence.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}