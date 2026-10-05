"""Run the production V2.2 historical analysis path and emit a compact JSON audit."""

import argparse
import json
import sys

from app.application_v2.analyze_historical import analyze_historical_decision_point
from app.application_v2.reconstruct_race_state import HistoricalRaceStateRequest
from app.data_sources.openf1_client import OpenF1Error
from app.models.historical_v2 import HistoricalAnalysisResponse


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_key", type=int)
    parser.add_argument("driver_number", type=int)
    parser.add_argument("decision_lap", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = analyze_historical_decision_point(HistoricalRaceStateRequest(
            openf1_session_key=args.session_key,
            focal_driver_number=args.driver_number,
            decision_lap=args.decision_lap,
        ))
    except OpenF1Error as exc:
        print(json.dumps({
            "decision_lap": args.decision_lap,
            "driver_number": args.driver_number,
            "error": "provider_unavailable",
            "message": str(exc),
            "session_key": args.session_key,
        }, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(2) from None
    response = HistoricalAnalysisResponse.from_result(result)
    focal = next(
        car for car in response.race_state.competitors
        if any(
            item.provider.lower() == "openf1"
            and item.resource_type == "driver_number"
            and item.value == str(args.driver_number)
            for item in car.external_ids
        )
    )
    pace = next(item for item in response.pace.competitors if item.competitor_id == focal.competitor_id)
    tyre = next(item for item in response.tyre_age_slope.competitors if item.competitor_id == focal.competitor_id)
    pace_quantiles = pace.diagnostics.quantiles if pace.diagnostics else None
    tyre_diagnostics = tyre.diagnostics
    summary = {
        "session": response.race_state.session.name,
        "event": response.race_state.session.event.name,
        "focal_competitor": str(focal.competitor_id),
        "driver_name": focal.driver_name,
        "decision_lap": args.decision_lap,
        "cutoff": response.race_state.observation_cutoff.isoformat(),
        "representative_pace_s_per_lap": pace.point_fit.estimate.value if pace.point_fit.estimate else None,
        "pace_quantiles_s_per_lap": None if pace_quantiles is None else {
            "p10": pace_quantiles.p10,
            "p50": pace_quantiles.p50,
            "p90": pace_quantiles.p90,
        },
        "pace_sample_count": pace.point_fit.diagnostics.included_laps,
        "pace_unavailable_reason": pace.point_fit.unavailable_reason,
        "tyre_age_slope_s_per_lap_per_lap": tyre.point_fit.estimate.value if tyre.point_fit.estimate else None,
        "tyre_sample_count": tyre.point_fit.diagnostics.included_laps,
        "tyre_unavailable_reason": tyre.point_fit.unavailable_reason,
        "slope_sign": tyre_diagnostics.nominal_sign if tyre_diagnostics else None,
        "sign_stable": tyre_diagnostics.sign_stable if tyre_diagnostics else None,
        "loo_envelope": None if tyre_diagnostics is None else {
            "lower": tyre_diagnostics.sensitivity_envelope.lower,
            "upper": tyre_diagnostics.sensitivity_envelope.upper,
        },
        "pace_quality": pace.data_quality.level,
        "tyre_quality": tyre.data_quality.level,
        "pace_point_model": pace.point_model_version.model_dump(),
        "tyre_point_model": tyre.point_model_version.model_dump(),
        "robustness_model": pace.robustness_model_version.model_dump(),
    }
    print(json.dumps(summary, indent=2, default=str, sort_keys=True))


if __name__ == "__main__":
    main()
