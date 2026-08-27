# V61 run 2: rigid geometry vs compliant-foot screening

## Purpose

Test whether the thin-foot compliance model is actually required by the existing free-decay data, rather than only being geometrically plausible.

The source raw data remains in the research data set. This repository stores only the derived peak/zero-cross pairs used for this screening:

`data/processed/v61_run2_free_decay_peak_zero_pairs.csv`

The 11 transitions use synchronized video peak angle as the peak amplitude and RWLOG gyro rate interpolated at the corresponding video zero crossing.

## Models

- **A**: historical complete rigid circle
- **B**: rigid STEP split arc with the 10 mm central gap
- **C**: Model B plus the symmetric two-foot quasi-static vertical-compliance screening model

For each starting peak side, a separate scale parameter is fitted between potential energy and zero-cross rate. Model C additionally sweeps one shared per-foot effective stiffness `k`.

## Result

| Model / stiffness | combined rate RMSE [deg/s] |
|---|---:|
| A complete rigid circle | 6.973 |
| B rigid STEP split arc | **2.639** |
| C, k=5 kN/m | 8.262 |
| C, k=10 kN/m | 4.630 |
| C, k=20 kN/m | 3.440 |
| C, k=50 kN/m | 2.910 |
| C, k=100 kN/m | 2.765 |
| C best within search up to 1 MN/m | 2.650 at the upper bound |

The Model-C optimum runs toward `k -> infinity`, i.e. back toward rigid Model B. The fit does **not** support a soft vertical-spring contact model for this free-decay segment.

Leave-one-out cross-validation gives:

| Model | LOO RMSE [deg/s] |
|---|---:|
| A | 8.760 |
| B | **3.333** |
| C | 3.351 |

In the Model-C LOO fits, the median selected stiffness is again the search upper bound (`1 MN/m`).

As another sensitivity statement, Model C must use approximately

`k >= 51 kN/m per foot`

before its in-sample RMSE is within +10% of Model B. This is a **model-equivalent lower bound**, not a measured physical stiffness.

## Interpretation

This result changes the priority of the flexibility hypothesis.

1. The STEP central-gap correction remains strongly supported: Model B is much better than complete-circle Model A.
2. The naive cantilever/vertical-spring softness estimate is not supported by the free-decay peak-to-zero-rate relation.
3. Visible foot bending can still be real. The effective load path may be much stiffer than the simple beam assumption because of curvature, distributed contact, the reinforced root, and the actual deformation mode.
4. Foot flexibility may still affect **impact/contact timing, hysteresis, side asymmetry, or the actively rebuilt zero-cross event** without appearing as a soft quasi-static vertical spring in free decay.
5. Therefore the physical stiffness test is still worth doing, but current data says not to replace Model B with a soft Model C yet.

## Consequence for the V61 failure investigation

The current best working hierarchy is:

- use **Model B** as the baseline passive rocker geometry;
- measure left/right foot stiffness and hysteresis to bound any compliance correction;
- then investigate the remaining post-rebuild directional residual using wheel speed/current/history and contact-event timing.

This avoids over-attributing the V61 failure to visible foot bending.

## Reproduction

```bash
python analysis/fit_free_decay_compliance.py
```

The script also reports the stiffness sensitivity and LOO comparison.
