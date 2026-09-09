# Units and numerical semantics

V2 uses explicit suffixes at boundaries: `_s`, `_ms`, `_laps`, `_c`, `_mps`, `_fraction`, and `_at`. SI units are preferred. Seconds are the default duration and must be named (`lap_time_s`, `pit_loss_s`). A canonical `Gap` uses exactly one of `seconds` or positive whole `laps`. Milliseconds are allowed only for raw timing precision or latency and use `_ms`; conversion occurs at the adapter boundary. Degradation is `s/lap/lap`.

- Laps and positions are integers starting at 1; tyre age and stop counts may be 0.
- Timestamps are usable timezone-aware ISO 8601 instants normalised to UTC by canonical validation. Naive or unusable `tzinfo` values are invalid.
- Temperatures are Celsius; wind is metres per second.
- Probability is a number in `[0,1]` for a named event over a defined sample space. A percentage is a displayed probability or fraction multiplied by 100 and must name its source.
- Missing observations are `null`/`None`, never zero, empty text, or a fabricated estimate. Unknown categorical state uses an explicit `unknown` member where useful.
- Confidence is an ordinal assessment (`low`, `medium`, `high`, `unknown`) with a documented rubric; it is not probability.
- A point estimate needs no fabricated spread. A distribution names its family. Empirical P10/P50/P90 summaries, bounded/statistical intervals and normal parameters are distinct representations; only the normal form requires a standard deviation.
- Scenario frequency uses a field named `frequency` plus matching/total scenario counts. It is descriptive and is never exposed through a probability-named field.

The following terms are not interchangeable:

| Term | Meaning |
|---|---|
| probability | Likelihood of a defined event under a defined model/sample space |
| confidence | Strength/quality of support for a conclusion under a rubric |
| preference share | Fraction of evaluated scenarios where one candidate outranks the other supplied candidates |
| percentile | Value below which a stated fraction of a distribution lies |
| uncertainty interval | Bounds plus coverage or construction method |
| scenario frequency | Observed fraction of sampled scenarios satisfying a condition |

V1 fields named `win_probability` and `win_percentage` measure candidate preference frequency, not race-winning probability. They remain only for compatibility and are forbidden terminology in new V2 contracts.
