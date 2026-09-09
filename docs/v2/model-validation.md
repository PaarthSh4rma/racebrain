# Model validation contract

A ValidationCase contains immutable canonical input at a recorded no-hindsight cutoff, model/config versions and config hashes, seed, prediction, data-quality report, and an observed outcome loaded only after prediction is frozen. Partitioning is chronological and grouped by event/session. Individual laps must never be randomly split where the same event could leak across train and test. Preferred evaluation is rolling-origin/forward-event evaluation.

Validation engines return a strict ValidationResult: case ID, non-empty typed ValidationMetric values with explicit units and optional sample counts, warnings, model versions and provenance. Untyped metric dictionaries are not analytical contracts, and acceptance thresholds remain outside the result until established from baselines.

For in-event updating at lap N, the model may use pre-event knowledge plus observations available through that decision cutoff only. Future laps from the same event remain excluded from features, calibration and selection at that prediction point.

Planned metrics:

| Quantity | Candidate metrics |
|---|---|
| lap time | MAE, RMSE, bias, error by circuit/compound/stint phase/status |
| pace residual | residual distribution, autocorrelation, bias by traffic/weather/fuel proxy |
| degradation slope | slope error and sign accuracy with uncertainty on observed slope |
| pit loss | absolute error and bias by circuit and track status |
| rejoin | position accuracy, gap MAE, nearby-competitor precision/recall |
| stop window | observed stop inclusion/coverage plus width; descriptive unless team intent is known |
| uncertainty | empirical interval coverage, sharpness, PIT/reliability diagnostics appropriate to distribution |
| decision regret | predicted counterfactual delta versus best defensible reconstructed alternative, labelled model-dependent |

Thresholds are not invented now. First establish frozen naive and V1 baseline distributions across representative events, inspect segment/sample sizes, then FDEs approve thresholds and regression budgets. Report central tendency, tails, confidence intervals and missingness; never accept a model because traces look plausible.

OpenF1 alone cannot validate tyre carcass condition, set identity/remaining life, fuel load, energy deployment, setup, driver instructions, true clean-air potential, team intent, precise pit-lane operational loss, or outcomes for actions not taken. Counterfactual regret therefore requires an explicitly validated counterfactual model and cannot be observed directly. Stop-window “correctness” cannot be inferred merely from the actual stop lap.
