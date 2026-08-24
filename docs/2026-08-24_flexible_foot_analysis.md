# 2026-08-24 Thin-foot compliance audit

## Scope

This note extends the rigid STEP contact audit with the observation that the printed feet bend slightly. CAD material/mass properties are **not** used. STEP supplies geometry only; stiffness/damping remain measured or fitted parameters.

## 1. Coordinate and STEP geometry used

The lateral rocking plane is X-Z and the rocking axis is Y. For each lower foot arc, STEP surfaces show:

- outer cylindrical radius: `150.0 mm`
- inner cylindrical radius: `148.5 mm`
- radial shell/strip thickness: **`1.5 mm`**
- arc width in Y: **`56.0 mm`**
- inner contact edge: `|X| = 5 mm`
- reinforced/root transition visible around `|X| = 37 mm`
- outer arc edge: `|X| = 45 mm`

Using the outer radius, the arc length from the inner edge (`X=5 mm`) to the reinforced/root transition (`X=37 mm`) is about `L = 32.385 mm`.

The complete-circle bottom that is missing between the two feet is only

`R - sqrt(R^2-a^2) = 0.08336 mm`

below the inner edges (`a=5 mm`). Therefore sub-millimetre foot deformation can be large compared with the geometric feature that created the rigid `1.910 deg` contact-mode boundary.

## 2. Why flexibility cannot be dismissed a priori

A first screening treats the thin curved strip as a rectangular cantilever bending through the 1.5 mm radial thickness:

`I = b t^3 / 12 = 1.575e-11 m^4`

and

`k ~= 3 E I / L^3`.

This is deliberately only an order-of-magnitude model. Curvature, the root geometry, layer orientation, print voids, material, and distributed contact can all change the real stiffness substantially.

For sensitivity only, sweeping `E=1..3 GPa` gives:

| E [GPa] | k [N/m] | deflection at half body weight [mm] | deflection at full body weight [mm] |
|---:|---:|---:|---:|
| 1.0 | 1391 | 0.704 | 1.408 |
| 1.5 | 2087 | 0.469 | 0.939 |
| 2.0 | 2782 | 0.352 | 0.704 |
| 2.5 | 3478 | 0.282 | 0.563 |
| 3.0 | 4173 | 0.235 | 0.469 |

The body weight used here is the previously measured `m=0.1997 kg`; these rows do **not** claim the printed foot's Young's modulus is any of the swept values.

The stiffness for which the half-weight static deflection equals the entire rigid-gap sagitta (0.08336 mm) is about

`k ~= 11.75 kN/m per foot`.

So if the measured effective foot stiffness is below roughly 12 kN/m, the deformation under ordinary static load is already larger than the geometric sagitta responsible for the rigid central contact transition. In that case a rigid contact model is not physically self-consistent near upright.

## 3. Double-support effect near upright

A useful screening model represents the two inner foot regions as vertical springs at `X=+/-a`. Under a small roll angle, their undeformed height difference is approximately

`Delta z = 2 a sin(theta)`.

For identical per-foot stiffness `k`, both feet can remain compressed while

`2 a sin(|theta|) <= m g / k`.

This gives the approximate high-foot unload angle

`theta_ds ~= asin(m g / (2 a k))`.

Examples:

| k [N/m per foot] | half-weight compression [mm] | theta_ds [deg] |
|---:|---:|---:|
| 5000 | 0.196 | 2.245 |
| 7500 | 0.131 | 1.496 |
| 10000 | 0.098 | 1.122 |
| 11747 | 0.083 | 0.955 |
| 15000 | 0.065 | 0.748 |

The rigid split-arc tangent boundary was `1.910 deg`. Therefore the actual sequence of contacts can differ materially from the rigid sequence depending on stiffness. In particular, for a softer foot the higher foot can remain in contact while the lower side has already approached or entered circular-arc contact. That is a multi-contact problem, not a single rigid rolling contact.

## 4. Static-stability diagnostic

The same two-spring screening model gives, near zero,

`U(theta) ~= (k a^2 - m g H / 2) theta^2`.

Thus its local upright-stability threshold is

`k_crit = m g H / (2 a^2)`.

Using `m=0.1997 kg`, `H=0.120 m`, `a=0.005 m`:

`k_crit ~= 4.70 kN/m per foot`.

This is useful as a falsification check, not a final design equation. If the actual machine has a robust centered upright equilibrium, a fitted Model-C stiffness below this value would mean that the independent-vertical-spring approximation is missing important shell/root/contact stiffness or geometry.

## 5. Consequences for the previous decay model

There are now three distinct models to compare:

- **Model A**: complete rigid circle (historical approximation)
- **Model B**: rigid STEP split arc (10 mm center gap)
- **Model C**: split arc plus compliant foot/contact screening

Model B already changed the potential energy and improved the V61 free-decay zero-cross-speed comparison relative to Model A. Foot compliance can partially undo or reshape that Model-B correction because the loaded body settles and load is shared between two deformable contacts near upright.

Therefore it is possible for a simple complete-circle model to look empirically reasonable in some ranges for the wrong reason: geometric-gap error and compliance error can partially cancel. This is one reason not to infer physical parameters from a single fitted `I_EFF` alone.

## 6. Does foot flexibility explain the whole V61 post-rebuild failure?

Not yet, and probably not by itself.

A simple beam-frequency screen for the 32.4 mm strip is of order hundreds of hertz for generic polymer-scale stiffness/density sensitivity values. That suggests the structural bending response itself is likely much faster than the approximately hertz-scale body rocking motion. Thus the strongest first-order effect is expected to be **quasi-static contact/load redistribution and viscoelastic/contact loss**, rather than a slowly stored elastic state that necessarily survives an entire half cycle.

Foot deformation can still contribute to V61 failure through:

- contact-mode timing around zero crossing,
- state-dependent energy loss/hysteresis,
- side-to-side stiffness differences,
- altered zero-cross rate for the same body peak,
- interaction with the reaction-wheel impulse exactly when the contact state is changing.

The remaining direction-dependent post-rebuild residual should therefore still be tested against wheel speed/current history after the contact model is corrected.

## 7. Recommended physical identification test

Measure left and right feet separately.

1. Clamp/support the foot root/upper structure so the same region seen in STEP is constrained.
2. Apply force at the inner contact edge in the direction produced by the floor during use.
3. Use points covering approximately `0 -> 2 N` (body weight is about `1.96 N`).
4. Record displacement relative to the reinforced/root region, not relative to the camera/background.
5. Perform at least three loading and unloading cycles.
6. Fit `F = k delta + F0` over the approximately linear region.
7. Compare loading/unloading curves to quantify hysteresis.
8. Repeat for left and right feet to obtain `k_L`, `k_R`.

The most useful first numbers are:

- deflection under about `0.98 N` (half weight),
- deflection under about `1.96 N` (full weight),
- left/right stiffness,
- loading/unloading hysteresis.

Once these are measured, Model C can stop using broad sensitivity values and the time-domain free-decay simulation can use experimentally grounded contact parameters.

## 8. Code added with this audit

- `model/foot_compliance.py`: STEP section geometry and compliance screening formulas
- `model/compliant_contact.py`: two-foot quasi-static load-sharing model
- `analysis/estimate_foot_flexibility.py`: numerical sensitivity table
- `analysis/compare_model_abc.py`: CSV sweep for Models A/B/C
- `tests/test_geometry_and_compliance.py`: regression tests for key geometry/contact relations

Important: Model C is explicitly labeled a screening model until foot stiffness is measured. It should not be used as a final controller model yet.
