export type RaceSession = {
  session_key: number;
  session_name: string;
  session_type: string;
  country_name: string;
  circuit_short_name: string;
  location: string;
  year: number;
  date_start: string;
};

export type Driver = {
  driver_number: number;
  broadcast_name: string;
  full_name: string;
  name_acronym: string;
  team_name: string;
  team_colour: string;
};

export type LiveStrategyResponse = {
  session_key: number;
  driver_number: number | null;
  race_state_summary: {
    weather: {
      air_temperature_avg: number;
      track_temperature_avg: number;
      humidity_avg: number;
      wind_speed_avg: number;
      rainfall_detected: boolean;
    };
    race_control: {
      total_events: number;
      safety_car_events: number;
      red_flag_events: number;
      notable_events: string[];
    };
    driver_lap_summary: {
      laps_completed: number;
      average_lap_time: number;
      best_lap_time: number;
    };
  };
  strategy_call: {
    recommendation: string;
    call: string;
    tyre_risk: string;
    race_volatility: string;
    current_stint: {
      stint_number: number;
      compound: string;
      lap_start: number;
      lap_end: number;
      tyre_age_at_start: number;
    } | null;
    pace_context: {
      laps_completed: number;
      average_lap_time: number;
      best_lap_time: number;
    };
    weather_context: Record<string, unknown>;
    reasoning: string[];
  };
};