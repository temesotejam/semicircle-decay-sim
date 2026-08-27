# 2026-08-24 Historical cross-validation of Model-B CG height

## Question

Does the `H ~= 128 mm` Model-B CG-height estimate obtained from V61 run 2 generalize to older data, or is it only a V61-run-2 fit?

## Data used

`study_AT` is read-only. 54 historical pre-pulse Q-probe states were extracted from 9 runs:

- V55 robust reanalysis: run1, run2, run3
- V56 repeat-Q: run1, run2, run3
- V58 repeatability: run1, run2, run3

The source files are each run's `analysis/v49_qprobe_half_range_comparison.csv`. The derived rows retained only:

- dynamic predecessor amplitude `dynamic_H_prev_deg`
- bias-corrected zero-cross command rate `command_rate_bias_corrected_dps`
- travel/command side
- offline video predecessor amplitude for provenance/checking

These are **not pure passive identification transitions**. They occur before Q-probe pulses but can carry earlier active/wheel/contact history. Therefore they are used as an external generalization test, not to re-identify the physical CG height from scratch.

## Strict parameter-transfer test

The strongest test freezes not only the STEP geometry but also the direction-wise effective energy scales obtained from the V61 passive fit at `H=128.345 mm`:

- travel `+`: `J_eff = 0.795e-3 kg m^2`
- travel `-`: `J_eff = 0.928e-3 kg m^2`

No historical-run-specific J is fitted.

For each state the Model-B prediction is

`omega_pred = sqrt(2 U_B(Hprev; H) / J_eff_side)`.

Results over all 54 states:

| CG height | rate RMSE | bias (predicted - measured) |
|---|---:|---:|
| `H = 120 mm` | `7.373 deg/s` | `+6.175 deg/s` |
| `H = 128.345 mm` | **`3.705 deg/s`** | `-1.678 deg/s` |
| best H with V61 J frozen | **`126.933 mm`** | `-0.27 deg/s` near optimum |

Thus the historical data strongly reject `120 mm` under the transferred V61 Model-B scale. The old value systematically predicts too much zero-cross speed. Moving H into the `127--128 mm` region removes most of that systematic bias and roughly halves the RMSE.

## Version-level result

With V61 J still frozen, the pooled best H for each historical version is:

| Version | best H | RMSE |
|---|---:|---:|
| V55 | `127.023 mm` | `2.981 deg/s` |
| V56 | `126.020 mm` | `3.425 deg/s` |
| V58 | `127.665 mm` | `3.618 deg/s` |

The three independent experiment groups all prefer essentially the same CG-height region.

## Run-by-run result

The 9 independently optimized H values (J still frozen to V61 values) are:

| Run | best H [mm] | RMSE [deg/s] |
|---|---:|---:|
| V55 run1 | 128.595 | 2.657 |
| V55 run2 | 126.810 | 2.757 |
| V55 run3 | 125.665 | 2.929 |
| V56 run1 | 127.093 | 3.907 |
| V56 run2 | 125.175 | 2.500 |
| V56 run3 | 125.183 | 3.315 |
| V58 run1 | 126.860 | 3.354 |
| V58 run2 | 128.728 | 2.648 |
| V58 run3 | 126.975 | 4.267 |

Summary:

- mean: `126.787 mm`
- median: `126.860 mm`
- standard deviation: `1.229 mm`
- range: `125.175 .. 128.728 mm`

This concentration is much tighter than would be expected if the V61 `128 mm` result were merely an arbitrary single-run compensation.

## Geometry-only comparison with historical J refitted

A second test allows one effective J for each travel direction to be refitted on the 54 historical states. This is less strict, but it tests whether the new geometry itself generalizes.

- Model A, complete circle, `H=120 mm`: RMSE `4.161 deg/s`
- Model B, STEP split arc, `H=128.345 mm`: RMSE **`2.620 deg/s`**

RMSE reduction: **37.0%**.

The historical-data effective scales at Model B are approximately:

- travel `-`: `J_eff = 0.8247e-3 kg m^2`
- travel `+`: `J_eff = 0.8066e-3 kg m^2`

Again these are effective energy-fit scales, not rigid-body inertia.

## Implied effective J distribution at H=128.345 mm

Computing `J_i = 2 U_B(Hprev_i) / omega_i^2` for all 54 states gives:

- mean: `0.815e-3 kg m^2`
- median: `0.812e-3 kg m^2`
- standard deviation: `0.067e-3 kg m^2`

Version medians are roughly:

- V55: `0.808e-3`
- V56: `0.775e-3`
- V58: `0.827e-3 kg m^2`

Side medians are very close (`~0.816e-3` vs `~0.810e-3`). This is surprisingly stable given that these states come from experiments with active-history contamination. It is useful as an empirical range, but should not be interpreted as the physical rigid-body `I_G`.

## Important warning: do not estimate physical H from active-history states alone

If both H and direction-specific J are allowed to refit freely on these Q-probe states, H can drift to much larger values. That is a warning, not evidence that the true CG is that high: active-history/wheel/contact states can be absorbed into H and J.

Therefore the hierarchy remains:

1. identify physical/dynamic H from clean passive data (V61 passive segment + independent gyro/video cross-check),
2. use older active-history states only for transfer validation,
3. investigate their residuals as evidence of wheel/contact hidden state rather than forcing H to absorb them.

## Updated working conclusion

The V61 passive estimate `H ~= 128 mm` is not isolated. Older V55/V56/V58 states independently prefer approximately `127 mm` when the V61 direction-wise scale is transferred without refitting.

A defensible current working range is therefore

`H = 127--128 mm`

and the controller/simulator can continue to use

`H = 0.128 m`

as a rounded Model-B working value, with a practical uncertainty of a few millimetres until a new independent static CG measurement and dedicated passive-decay dataset are obtained.

The old `H=120 mm` value should remain in the repository as a historical/reference value, not as the current Model-B default.

## Reproduction

```bash
python analysis/cross_validate_cg_historical.py
```

Derived input table:

`data/processed/historical_qprobe_state_cross_validation.csv`
