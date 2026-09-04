# 2026-09-04 Dynamic left/right support-transfer audit

## Purpose

Test the hypothesis that the lateral support load does not jump instantaneously from one foot to the other around upright.  This follows the STEP compliance audit, which found that a large conservative foot-bending spring did not robustly improve the passive data.

The new model is deliberately reduced-order and is evaluated before changing the main Model-B baseline.

## Model D: finite-time support balance

Introduce a support-balance state

`-1 <= s <= +1`

with

- `s=-1`: left inner support dominates,
- `s=0`: equal left/right load share,
- `s=+1`: right inner support dominates.

Inside a candidate load-transfer angle window, the quasi-static desired balance moves continuously toward equal sharing as roll approaches zero.  The actual balance follows with

`ds/dt = (s_eq(theta) - s) / tau_tr`.

Outside the rigid central contact region, the exact Model-B circular-arc gravity torque remains unchanged.  Inside the central region the gravity/contact torque is approximated by the resultant inner-edge support position:

`Q = m g [ H sin(theta) - a s cos(theta) ]`.

The rigid Model B is nested as the limiting case `transfer_start=0`, `tau=0`.

Implementation:

- `model/dynamic_support_transfer.py`
- `analysis/evaluate_dynamic_support_transfer.py`

## Data 1: V61 run 2, peak -> zero crossing

The 11 synchronized free-decay transitions contain:

- video peak angle,
- peak time,
- gyro zero-cross rate,
- zero-cross time.

Unlike the earlier energy-only fit, this audit fits **both zero-cross rate and peak-to-zero transit time**.  Because the objective differs, the rate RMSE numbers below should not be directly compared with the earlier `2.639 deg/s` rate-only Model-B fit.

A separate effective inertia is fitted for each incoming side.  Model D additionally searches transfer-start angle and support-transfer time constant.

### Joint in-sample fit

| quantity | Model B rigid | Model D finite transfer |
|---|---:|---:|
| normalized joint objective | 0.020623 | **0.020171** |
| fitted `J-` [kg m2] | `9.10339e-4` | `8.97849e-4` |
| fitted `J+` [kg m2] | `1.128806e-3` | `1.124191e-3` |
| zero-cross-rate RMSE [deg/s] | 4.149 | **3.971** |
| transit-time RMSE [ms] | **27.91** | 28.08 |

Selected Model-D parameters:

`transfer_start = 0.500 deg`

`tau_tr = 2.0 ms`

Thus the training objective improves by only about 2.2%.  The rate fit improves by about 4.3%, while transit-time RMSE is essentially unchanged/slightly worse.

More importantly, both selected parameters sit at the **fast/small end** of the search.  V61 does not ask for a slow tens-of-milliseconds support exchange.

### Nested leave-one-out validation

For each held transition, all Model-D hyperparameters and side inertia values were re-selected on the remaining transitions.

| quantity | Model B rigid | Model D finite transfer |
|---|---:|---:|
| LOO rate RMSE [deg/s] | **4.803** | 5.403 |
| LOO transit-time RMSE [ms] | **30.84** | 31.97 |

Median Model-D parameters selected across LOO fits:

`transfer_start = 0.500 deg`

`tau_tr = 2.0 ms`

Therefore the small in-sample gain does **not** generalize.  The finite-time model is worse in both held-out rate and held-out transit time.

## What happens at zero crossing in the selected D model

The selected V61 model still retains some old-side support balance at the exact roll zero crossing because `s` has finite response time.

Across the 11 transitions, the signed support balance at zero is approximately

`|s_zero| = 0.17 ... 0.38`.

This is a model state, not a measured force fraction.  It only says that even a 2 ms first-order lag can carry memory through zero when the crossing speed is high.

The event residual pattern remains important:

- large-amplitude negative transition (`-12.22 deg`) is predicted much too fast in time (`194.6 ms` vs `254.8 ms`),
- small-amplitude transitions around `4 deg` are predicted too slow in time,
- the finite transfer state does not remove this amplitude-dependent transit-time mismatch.

This suggests that the remaining V61 mismatch is not explained by one common support-transfer time constant alone.

## Data 2: independent 2026-08-28 manual-release periods

The +/-4, +/-8, +/-12 and +/-15 deg passive manual-release data provide an independent period screen.  One global effective inertia is fitted for each model.

### Using the V61-selected transfer parameters

| quantity | Model B rigid | Model D with V61 parameters |
|---|---:|---:|
| fitted J [kg m2] | `8.39570e-4` | `8.33415e-4` |
| period RMSE [ms] | 24.07 | **22.88** |

So the V61-selected small/fast load-transfer correction improves the independent period RMSE by about **4.9%**.

This is the first positive signal for a support-transfer correction, but it is modest and must be weighed against the worse V61 LOO result.

### Period-only optimum

If transfer parameters are fitted only to the 8 manual-release period cases, the grid selects

`transfer_start = 2.500 deg`

`tau_tr = 2.0 ms`

with

`J = 8.11111e-4 kg m2`

and

`period RMSE = 19.88 ms`.

Relative to rigid Model B (`24.07 ms`), this is about a **17.4%** reduction.

However:

1. the preferred transfer-start angle (`2.5 deg`) is different from V61 (`0.5 deg`),
2. the preferred time constant again hits the smallest tested value (`2 ms`),
3. the fit is made to only eight median-period values, and initial manual-release velocity was not prescribed exactly.

Therefore the period-only improvement is evidence for a **contact-transition-region correction**, not yet evidence for a measurable 2 ms physical normal-force time constant.

## Main interpretation

The data distinguish two ideas that were previously mixed together.

### 1. Slow load-transfer lag

Not supported.

The fits consistently move toward the smallest time constant.  A 20--80 ms support-transfer lag is not needed by the current passive data.

### 2. Contact transfer beginning over a finite angular region

Still plausible.

The manual-release periods improve when the model begins redistributing support before/around the rigid `1.910 deg` point.  This is compatible with:

- finite contact patch,
- local shell flattening,
- distributed floor reaction rather than a mathematical point contact,
- slight early engagement of the opposite inner edge,
- small geometric rounding/chamfer,
- plate/shell load spreading.

The period-only best start `2.5 deg` is only about `0.6 deg` above the rigid STEP tangent boundary, so this is a local contact-transition correction rather than a wholesale change to the rocker geometry.

## Current decision

Keep **rigid Model B** as the default passive and control-simulator baseline.

Do not add a slow support-transfer state to the main reaction-wheel simulator yet, because nested V61 validation gets worse.

Keep Model D as an experimental sensitivity model.  The most promising next refinement is no longer a long first-order lag; it is a **small finite angular contact-transfer band with possible hysteresis/loss** around the rigid `1.910 deg` transition.

That next model should test separately:

- incoming arc -> inner-edge transition angle,
- outgoing inner-edge -> arc transition angle,
- a small energy-loss/hysteresis term per transition,
- left/right differences.

This directly targets the signal seen in the period data while avoiding an unsupported slow support-transfer assumption.
