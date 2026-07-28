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
  const [searchError, setSearchError] = useState<string | null>(null);
  const [driverError, setDriverError] = useState<string | null>(null);
  const [strategyError, setStrategyError] = useState<string | null>(null);

  async function handleSearchSessions() {
    setLoading(true);
    setSearchError(null);
    setDriverError(null);
    setStrategyError(null);
    setSessions([]);
    setDrivers([]);
    setSelectedSessionKey(null);
    setSelectedDriver(null);
    setLiveStrategy(null);

    try {
      const data = await getSessions({
        year,
        countryName,
        sessionName: "Race",
      });

      setSessions(data);
      setSelectedSessionKey(data[0]?.session_key ?? null);
      if (data[0]?.session_key) {
        try {
          const driverData = await getDrivers(data[0].session_key);
          setDrivers(driverData);
        } catch (error) {
          setDriverError(error instanceof Error ? error.message : "Failed to load drivers.");
        }
      }
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : "Failed to search sessions.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadStrategy() {
    if (!selectedSessionKey) return;

    setLoading(true);
    setStrategyError(null);
    setLiveStrategy(null);

    try {
      const data = await getLiveStrategy({
        sessionKey: selectedSessionKey,
        driverNumber: selectedDriver,
      });

      setLiveStrategy(data);
    } catch (error) {
      setStrategyError(error instanceof Error ? error.message : "Failed to generate strategy.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectSession(sessionKey: number) {
    setSelectedSessionKey(sessionKey);
    setSelectedDriver(null);
    setDrivers([]);
    setDriverError(null);
    setStrategyError(null);
    setLiveStrategy(null);
    setLoading(true);

    try {
      setDrivers(await getDrivers(sessionKey));
    } catch (error) {
      setDriverError(error instanceof Error ? error.message : "Failed to load drivers.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section
      data-testid="historical-card"
      className="mt-6 min-w-0 rounded-[2rem] border border-white/10 bg-black/40 p-4 backdrop-blur-xl sm:mt-8 sm:p-6"
    >
      <div className="mb-6">
        <p className="text-xs uppercase tracking-[0.35em] text-red-400">
          V3 Real Race Intelligence
        </p>

        <h2 className="mt-2 break-words text-2xl font-black sm:text-3xl">
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
            onSelectSession={(sessionKey) => void handleSelectSession(sessionKey)}
          />

          {searchError && <p className="text-sm text-red-300">{searchError}</p>}

          <DriverSelect
            drivers={drivers}
            selectedDriver={selectedDriver}
            onSelectDriver={setSelectedDriver}
          />

          {driverError && <p className="text-sm text-red-300">{driverError}</p>}

          <button
            onClick={handleLoadStrategy}
            disabled={loading || !selectedSessionKey}
            className="w-full rounded-2xl bg-red-600 px-4 py-4 text-sm font-black uppercase tracking-[0.15em] text-white transition hover:bg-red-500 disabled:opacity-50 sm:px-6 sm:tracking-[0.2em]"
          >
            {loading ? "Building Race State..." : "Generate Live Strategy Call"}
          </button>
          {strategyError && <p className="text-sm text-red-300">{strategyError}</p>}
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
