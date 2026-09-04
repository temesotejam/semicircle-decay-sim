# 2026-09-04 STEP cantilever-compliance audit

## Purpose

Test the new hypothesis that the thin printed rocker foot behaves as an angle-dependent cantilever and determine whether adding that compliance improves agreement with historical passive data.

This audit does **not** replace rigid Model B unless improvement survives validation.

## STEP geometry used

Source: `cad/Part_Studio_1.1.step`.

Recovered geometry relevant to lateral bending:

- outer rocker radius: `R = 150 mm`
- inner rocker radius: `148.5 mm`
- radial thin-shell thickness: `t = 1.5 mm`
- width along rocker axis Y: `b = 56 mm`
- inner contact edge: `|X| = 5 mm`
- brace/inner-surface boundary: **`|X| = 37 mm`**
- thin free arc from inner edge to that boundary: `L0 = 32.385 mm`

The STEP inner cylindrical face has an exact boundary at `X=37 mm` over the central `Y=6.727...15.727 mm` band (9 mm wide).  This is why `X=37 mm` is used as the primary geometry value.  The rest of the 56 mm-wide shell makes the true 3-D load path plate/shell-like rather than a perfect 1-D beam, so nearby effective-root positions are only a sensitivity test.

The thin strip second moment used for the screening beam is

`I = b t^3 / 12 = 1.575e-11 m^4`.

As circular contact moves outward, the free length is

`L(theta) = max(0, R*(theta_root - max(|theta|, theta_inner)))`

with

`theta_inner = asin(5/150) = 1.910 deg`

and

`theta_root = asin(37/150) = 14.280 deg`.

Therefore stiffness increases strongly with roll angle because cantilever vertical compliance scales as `L^3`.

## Reduced conservative Model C2

Rigid Model B potential remains the geometric baseline.

For a single loaded foot, thin-strip vertical compliance is

`C(theta) = L(theta)^3 / (3 E_eff I)`.

At upright, both inner edges share the load equally.  Near upright a symmetric two-support beam-tip stiffness is used until the high side unloads.  After unload, the low side carries full weight and its contact-dependent compliance is used.

The minimized quasi-static gravity + elastic correction is added to Model B.  `E_eff` is explicitly an **effective load-path bending modulus**, not a claim about bulk filament material.

The implementation is in:

- `model/step_cantilever_compliance.py`
- `analysis/evaluate_step_cantilever_compliance.py`

## Historical data set 1: V61 run 2 peak -> zero-cross rate

Derived synchronized validation pairs:

`data/processed/v61_run2_free_decay_peak_zero_pairs.csv`

There are 11 free-decay transitions.  Video supplies peak angle and RWLOG gyro supplies zero-cross rate.

As in the earlier Model-A/B audit, one rate/energy scale is fitted separately for each peak side.  Model C2 additionally fits one shared `E_eff`.

### Result at the actual STEP brace boundary x=37 mm

| model | in-sample rate RMSE [deg/s] | LOO RMSE [deg/s] |
|---|---:|---:|
| Model B rigid STEP | **2.639** | **3.333** |
| Model C2 best fitted E | 2.560 | 3.367 |

Best in-sample C2 modulus:

`E_eff = 12.04 GPa`.

The in-sample improvement is only about `3.0%`, while leave-one-out error becomes about `1.0% worse` than rigid Model B.  Therefore the small in-sample reduction at the actual STEP boundary is not a robust predictive improvement.

### Fixed-E sensitivity

| E_eff [GPa] | rate RMSE [deg/s] |
|---:|---:|
| 4 | 2.829 |
| 5 | 2.698 |
| 8 | 2.579 |
| 12 | 2.560 |
| 20 | 2.572 |
| 50 | 2.605 |
| 100 | 2.621 |
| rigid Model B | **2.639** |

A polymer-scale soft assumption around 1--3 GPa is substantially worse; for example the same endpoint screening gives about `3.83 deg/s` at 2 GPa, versus `2.64 deg/s` for rigid Model B.

### Effective-root sensitivity

To test the effect of the 3-D shell/load-spreading approximation, the effective root was varied around the exact STEP brace boundary.

| effective root X [mm] | fitted E_eff [GPa] | in-sample RMSE [deg/s] | LOO RMSE [deg/s] |
|---:|---:|---:|---:|
| 35 | 6.51 | 2.473 | **3.276** |
| 36 | 8.77 | 2.522 | 3.402 |
| **37 (STEP boundary)** | **12.04** | **2.560** | **3.367** |
| 38 | 16.95 | 2.588 | 3.351 |
| 39 | 24.72 | 2.609 | 3.379 |

A hypothetical `35 mm` effective root gives a small LOO improvement (`3.276` vs `3.333 deg/s`, about 1.7%).  However `35 mm` is not the STEP brace-contact boundary; `37 mm` is.  This sensitivity indicates that a more realistic 3-D shell/plate load path could be worth testing, but the present 1-D cantilever model does not justify changing Model B.

## Historical data set 2: 2026-08-28 passive periods

The independent manual-release data set contains +/-4, +/-8, +/-12 and +/-15 deg cases.  A conservative period consistency screen fits one global effective inertia `J` for each potential model.

This is a secondary screen because manual release velocity was not exactly prescribed and measured periods are medians over decaying cycles.

| model | period RMSE [s] | fitted J [kg m^2] |
|---|---:|---:|
| Model B rigid | **0.02418** | `8.4005e-4` |
| C2, E=8 GPa | 0.05875 | `9.4036e-4` |
| C2, E=12 GPa | 0.04763 | `9.1125e-4` |
| C2, E=20 GPa | 0.03788 | `8.8517e-4` |
| C2, E=50 GPa | 0.02908 | `8.5908e-4` |
| C2, E=100 GPa | 0.02644 | `8.4975e-4` |

The period data drive the model toward the rigid limit.  No finite soft-compliance case tested at the actual `37 mm` boundary improves on Model B.

## What the fitted scale means physically

At the V61 best-fit `E_eff = 12.04 GPa` and the actual root `x=37 mm`:

- inner-edge equivalent vertical stiffness per foot: `16.75 kN/m`
- half-body-weight inner-edge deflection: `0.0585 mm`
- full-body-weight inner-edge deflection: `0.1169 mm`
- thin free length at 8 deg: `16.44 mm`
- cantilever tip vertical deflection at 8 deg/full weight: `0.0153 mm`
- cantilever slope at 8 deg/full weight: `0.0800 deg`

Thus the historical data prefer an effective load path much stiffer than the earlier simple `E=1..3 GPa` screening assumption.  The previous order-of-magnitude estimate of roughly several tenths of a degree at 8 deg is not supported as a conservative quasi-static deformation in the passive data.

## Interpretation

1. The STEP observation is still correct: the 1.5 mm rocker shell is geometrically the most compliant-looking region and its free length changes strongly with contact position.
2. The exact STEP brace boundary is at `X=37 mm`, but it is only part of a 3-D shell/brace load path; a 1-D beam is therefore an approximation.
3. At the actual 37 mm geometry, adding conservative compliance slightly improves training fit but worsens cross-validation, while the independent 2026-08-28 period screen also gets worse.
4. A fitted high effective stiffness can represent curvature/shell action, reinforced load transfer, print orientation, distributed contact, neighboring structure, and the fact that the real load path is not a free rectangular beam.
5. A 35 mm *effective* root gives a tiny cross-validated gain, which suggests that 3-D load spreading deserves a more realistic shell model if we continue this direction; it is not enough evidence to replace Model B.
6. Therefore **rigid Model B remains the best passive baseline**.  Do not put C2 into the reaction-wheel control simulator as the default physics yet.
7. Real foot flexibility may still matter through non-conservative mechanisms that this conservative screen cannot capture: contact timing, local impact, hysteresis, slip, print damping, left/right stiffness differences, and transient deformation during RW input.

## Decision

Keep Model B as the current baseline.

Keep C2 as a sensitivity model.  The next useful validation, if foot flexibility is pursued, is either direct static/video stiffness measurement or a 3-D shell/plate reduced model that respects the partial 9 mm brace attachment seen in STEP.  Do not force the passive data to identify a large conservative beam deformation that cross-validation does not support.
