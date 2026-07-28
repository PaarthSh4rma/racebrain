# Historical Decision Replay implementation note

## Existing hindsight-leakage paths

The legacy historical flow downloads complete-session laps, stints, weather, and
race-control records before producing a strategy call. `build_race_state`
averages weather across the whole session, counts every later interruption,
summarises every completed lap, and passes every stint to
`generate_live_strategy_call`. That service selects the highest-numbered stint,
which is normally the driver's final stint. A recommendation requested for an
earlier race moment therefore incorporates future weather, future safety cars,
future lap pace, and future pit stops.

The `/live-strategy` endpoint is retained for compatibility, but the new replay
flow does not call it.

## Replay boundary

Historical Decision Replay selects one completed driver lap. When that lap has a
positive duration, it is eligible as a decision lap. When it also has a start
timestamp, start plus duration is the cutoff. If the timestamp is unavailable,
lap-number filtering is used and timestamp-only weather or race-control data is
excluded because it cannot be proven knowable. Lap start alone is never presented
as a completed-lap cutoff.

Driver laps are bounded by lap number. Stints beginning later are excluded and
the active stint is truncated to the decision lap. Weather and race-control
records are bounded by the derived timestamp; lap-numbered race-control records
are additionally bounded by lap. Record counts and excluded-future counts are
returned with incomplete-data warnings.

Alternative calls use a transparent deterministic strategy score over the same
configurable lap horizon under shared sampled pace and pit-loss conditions. It
does not claim to model competitors, traffic, undercuts, or race-win probability.

Tyre-risk thresholds are deliberately simple: soft, medium, and hard compounds
become high risk at estimated ages 18, 28, and 42 laps, with medium risk beginning
at 70% of those values. Pace is marked degrading or improving when the bounded
five-lap average differs from the preceding bounded five-lap average by more than
0.35 seconds per lap. Missing bounded inputs reduce recommendation confidence,
and any completeness warning prevents high confidence.

OpenF1 responses use a bounded, per-process, best-effort memory cache with
endpoint-specific expiry. It is neither shared persistence nor a database.
Consumers receive copies so replay processing cannot mutate cached payloads.
