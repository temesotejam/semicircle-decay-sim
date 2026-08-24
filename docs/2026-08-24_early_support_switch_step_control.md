# 2026-08-24 Early support-switch step-length control

## Working mechanism hypothesis

The current mechanism is best separated into four roles:

1. **Roll motion / reaction wheel** unloads one leg and determines when the swing foot is allowed to return to the floor.
2. **The unloaded rigid leg+foot assembly** swings passively about the hip X-axis under gravity.
3. **The hip hard stops** bound the maximum swing coordinate to `q in [-20, 0] deg`, therefore bounding the maximum geometric step.
4. **Fore-aft body balance and stance geometry** become especially important after first contact, when the new foot must actually accept load and become the next stance foot.

This means the reaction wheel does not need to prescribe the fore-aft leg angle directly. It can instead control **support-transfer timing**. If support is transferred before the swing leg reaches `q=-20 deg`, the resulting step can be shorter than the stop-to-stop maximum.

## Important wording: foot alone vs rigid leg+foot assembly

The knee-like intermediate connection and the ankle are confirmed fixed, so the moving passive body is the **entire leg+foot rigid assembly**.

A uniform-density STEP shape proxy gives the following CG directions from the hip:

| shape proxy | CG angle from downward vertical |
|---|---:|
| upper part only | 60.000 deg |
| lower part only | 35.919 deg |
| foot solid only | 8.515 deg |
| whole rigid leg+foot group | **32.747 deg** |

Therefore the current geometry screening supports the idea that the **whole rigid leg+foot mass distribution** can drive the passive swing toward the `q=-20 deg` stop. It does **not** support saying that the literal foot solid alone is sufficient: with the equal-density proxy, the foot-only CG is only 8.515 deg from vertical and would not have enough gravitational potential to reach `q=-20 deg` from rest at `q=0` by itself.

Actual component masses must still be measured before this is treated as a physical CG result.

## Gravity-direction screening

For the whole rigid leg+foot equal-density STEP proxy:

- CG relative to hip: `(Y, Z) = (21.883, -34.024) mm`
- CG angle from downward vertical at the STEP pose: `32.747 deg`
- `I_hip / m = 2532.014 mm^2`

At zero body fore-aft pitch, the gravity torque points toward decreasing `q` over the entire allowed range `[-20, 0] deg`.

The body pitch at which gravity torque becomes exactly zero at the `q=-20 deg` stop is about

`alpha = -12.747 deg`.

The frictionless energy boundary at which `q=-20 deg` has the same potential as the released `q=0 deg` state is about

`alpha = -22.747 deg`.

So in this **geometry-only proxy**, moderate fore-aft body pitch changes the swing speed but does not dominate the swing direction. This is consistent with the working interpretation that fore-aft balance is more important for the subsequent support/fixation phase than for generating the initial swing. This statement still needs measured leg masses and joint-friction validation.

## Variable geometric step from early support transfer

The ankle center moves monotonically in STEP-Y as `q` goes from `0` to `-20 deg`.

Maximum stop-to-stop ankle-center travel:

`20.904 mm`.

Selected intermediate values:

| swing angle `q` | ankle-center travel from `q=0` | fraction of maximum |
|---:|---:|---:|
| 0 deg | 0.00 mm | 0% |
| -5 deg | 5.20 mm | 24.9% |
| -10 deg | **10.44 mm** | **49.9%** |
| -15 deg | **15.69 mm** | **75.1%** |
| -20 deg | **20.90 mm** | **100%** |

Thus the STEP kinematics directly support the proposed variable-step mechanism: a support switch at an intermediate `q_switch` selects an intermediate geometric stride coordinate.

This is ankle-center travel, not yet the final ground-contact step length. With nonzero fore-aft foot pitch, the first floor contact can occur at a front/rear edge of the foot, so true contact-point step length must be handled separately.

## Ideal passive swing time scale

With the equal-density STEP proxy, zero body pitch, zero joint friction, a fixed/nonaccelerating hip, and release from rest at `q=0`, the model reaches the `q=-20 deg` stop in approximately

`95.70 ms`

with a pre-impact speed of about

`-371.7 deg/s`.

Examples:

| `q` | ideal proxy time from release | ankle travel |
|---:|---:|---:|
| -5 deg | 45.9 ms | 5.20 mm |
| -10 deg | 65.8 ms | 10.44 mm |
| -15 deg | 81.7 ms | 15.69 mm |
| -20 deg | 95.7 ms | 20.90 mm |

These times are **not physical predictions yet**. Real hip friction, actual mass distribution, moving-hip acceleration, contact, and stop compliance can change them substantially. The time values are used only to show that early support switching is dynamically meaningful on a sub-cycle time scale.

## Reaction-wheel roll as the touchdown selector

Using the actual STEP foot solids, zero fore-aft body pitch, right foot as stance candidate, and left foot as swing candidate, first possible swing-foot floor contact is defined kinematically by

`z_min(swing foot) - z_min(stance foot) = 0`.

For an illustrative fixed stance angle `q_stance=-20 deg`, the required roll threshold is:

| `q_swing` | geometric travel | touchdown roll |
|---:|---:|---:|
| 0 deg | 0.00 mm | -17.07 deg |
| -5 deg | 5.20 mm | -13.31 deg |
| -10 deg | 10.44 mm | **-9.34 deg** |
| -15 deg | 15.69 mm | **-5.09 deg** |
| -17.5 deg | 18.30 mm | -2.68 deg |
| -20 deg | 20.90 mm | **0.00 deg** |

The sign is the STEP/right-hand roll convention. Positive roll lowers the right/support side and raises the left/swing side. To make the left swing foot touch before it reaches the stop, the body must therefore roll back toward, and in this fixed-stance example past, the opposite side earlier.

This is exactly the proposed reaction-wheel role: **change the roll trajectory so the swing foot regains ground contact at the desired intermediate swing angle.**

## Stance-leg state matters

The touchdown roll is not a function of `q_swing` alone. It also depends on the stance-leg angle.

At zero fore-aft body pitch:

- if `q_stance=-20 deg`, `q_swing=-10 deg` touches at roll about `-9.34 deg`;
- if `q_stance=-15 deg`, the same `q_swing=-10 deg` touches at about `-6.93 deg`;
- if `q_stance=-10 deg`, the two feet are symmetric at `q=-10 deg`, so touchdown is at `0 deg` roll.

Therefore a useful reduced control state is at least

`(q_swing, q_stance, theta_roll)`.

Fore-aft body pitch `alpha` will later be added explicitly because it changes the foot-edge contact mode and the post-contact load-transfer condition.

## Control interpretation

A natural control hierarchy is:

1. choose target geometric step `L_ref`,
2. invert the audited geometry to obtain target swing angle `q_ref`,
3. let the unloaded leg swing passively toward `q_ref`,
4. use reaction-wheel roll control to move toward the touchdown boundary appropriate for the current stance state,
5. detect actual ground contact / support transfer,
6. after contact, use fore-aft balance/contact dynamics to determine whether the new foot successfully becomes the stance foot.

For example, the geometry inversion gives approximately:

- `L_ref = 5 mm` -> `q_ref = -4.811 deg`
- `L_ref = 10 mm` -> `q_ref = -9.581 deg`
- `L_ref = 15 mm` -> `q_ref = -14.343 deg`
- `L_ref = 20 mm` -> `q_ref = -19.129 deg`

This makes step-length control fundamentally a **support-switch / touchdown-timing problem**, rather than a direct leg-position actuator problem.

However, the final controller should not use elapsed time alone. The ideal proxy reaches `q=-10 deg` at about 65.8 ms, but real joint friction and body motion will move that timing. A robust controller should ultimately use an observed/estimated swing state `q_swing` and current stance/body state, with time only as a fallback or predictor.

## What is not yet modeled

- measured leg/foot component masses and physical CG
- hip joint friction
- moving-hip inertial forcing from body motion
- time-varying fore-aft body pitch
- foot-edge impact and restitution
- static/dynamic floor friction
- normal-load transfer after first contact
- whether first contact actually becomes a stable stance contact

No guessed coefficients are introduced for these terms.

## Reproduction

Geometry/ideal swing map:

```bash
python analysis/analyze_early_support_switch.py --csv passive_swing_step_map.csv
```

STEP touchdown-roll map:

```bash
python analysis/audit_early_touchdown_roll_map.py \
  "Part Studio 1.1.step" \
  --pitch 0 \
  --csv touchdown_roll_map_pitch0.csv
```

Uniform-density shape proxy extraction:

```bash
python analysis/extract_leg_uniform_density_proxy.py \
  "Part Studio 1.1.step" \
  --json leg_uniform_density_proxy.json
```
