# 2026-08-24 Mechanism kinematics / contact audit

## Scope

This audit determines how the leg+foot rigid body can move relative to the body using the supplied STEP geometry plus confirmed real-assembly semantics.

The separate fixed baseline repository is not modified. This work is only in `semicircle-decay-sim`.

Source STEP used for the recorded result:

- file: `Part Studio 1.1.step`
- SHA-256: `e268a25352145499ac5eb2602f635f547d3d6581199b257ca2c1f72aba44f4c8`
- solid count: 10

## 1. Confirmed rigid-body grouping

The STEP contains separate solids at bolted/fixed connections, so STEP solid count must not be treated as mechanism DOF count.

Confirmed from the real assembly:

- upper/lower leg connection: **fixed**
- ankle connection: **fixed**
- hip connection: **revolute**

Therefore the moving rigid groups are:

- left leg + foot: STEP solids `0 + 6 + 7`
- right leg + foot: STEP solids `8 + 5 + 9`

For collision auditing, the central body group is STEP solids `1 + 2 + 3 + 4`.

The apparent intermediate "knee" and the ankle are geometry/assembly connections, not generalized coordinates.

## 2. Hip rotation axis

X-parallel cylindrical surfaces were extracted from STEP and their centerlines compared between the upper leg and body.

Both left and right sides uniquely share the centerline

```text
direction = (1, 0, 0)
Y = 0 mm
Z = -12 mm
```

Thus the leg generalized coordinate is rotation around the STEP X axis through

```text
r_hip = (X, 0, -12 mm).
```

The leg therefore moves in the STEP Y-Z plane.

Important: STEP Y is confirmed as the physical fore-aft axis, but the sign of STEP `+Y` has not yet been mapped to the real walking-forward direction. Until that is checked from hardware/video, this audit uses only `+Y` / `-Y`, not "forward" / "backward" labels.

## 3. Fixed connection reference geometry

The X-axis cylinder centerlines also recover the fixed assembly locations:

- hip: `(Y,Z) = (0, -12) mm`
- upper/lower fixed connection: `(44.1672956, -37.5) mm`
- fixed ankle/foot connection: `(11.2273845, -71.1398672) mm`

Reference distances:

- hip -> fixed bend: `51.000 mm`
- fixed bend -> ankle: `47.0816 mm`
- hip -> ankle: `60.1962 mm`

The complete bent leg+foot assembly still behaves as **one rigid body around the hip**.

## 4. CAD hard-stop range

The complete leg rigid group was virtually rotated around the recovered hip axis. For every angle, boolean intersection volume with the central body group was evaluated.

No arbitrary cylindrical exclusion volume was used around the hip. This is important because the non-circular hip geometry itself is the mechanical stop.

The collision-free interval containing the STEP assembly pose is:

```text
q_min = -20 deg
q_max =   0 deg
```

Numerical boolean-boundary results were:

- left: approximately `[-20.000014, +0.000015] deg`
- right: approximately `[-20.000008, +0.000015] deg`

The tiny numerical offsets are boolean/tolerance effects. The intended geometric result is clearly

```text
-20 deg <= q <= 0 deg.
```

Penetration begins immediately outside both boundaries:

- at `q ~= +0.1 deg`, the left leg penetrates central-frame solid 3 by about `0.0755 mm^3`
- at `q ~= -20.1 deg`, penetration is about `0.1579 mm^3`

Both first penetrations occur around the hip housing. Solids 1, 2 and 4 are not the first stop contacts; the actual CAD stops are in the central-frame geometry (solid 3).

### Consequence

The leg is **not** a freely rotating pendulum. It is a passive rigid link with a roughly 20-degree hard-limited swing.

## 5. Leg orientation through the allowed range

Using the hip-to-ankle vector, the STEP pose (`q=0`) places the ankle direction at

```text
+10.749 deg
```

relative to the vertically downward direction in the Y-Z plane.

At the opposite hard stop (`q=-20 deg`) it is approximately

```text
-9.251 deg.
```

Thus the permitted swing is almost centered around vertical:

```text
-9.25 deg ... +10.75 deg.
```

The ankle Y coordinate changes from approximately

```text
Y = +11.227 mm   at q = 0 deg
Y =  -9.677 mm   at q = -20 deg
```

for a total fore-aft travel of about

```text
20.904 mm
```

at the ankle center. This is only the ankle-center travel; the fixed foot geometry also rotates with the leg.

## 6. Left-leg / right-leg collision

The two rigid leg groups have a minimum X separation of about `10 mm` in the STEP pose. Hip motion is rotation around X, which does not change any point's X coordinate.

Therefore, under the currently identified hip DOF alone,

```text
left leg + foot and right leg + foot cannot geometrically intersect.
```

No artificial left/right collision torque is needed for the first kinematic model.

## 7. How contacts should be represented in the model

Different physical contacts must not be collapsed into one generic collision rule.

### 7.1 Fixed internal connections

The upper/lower connection and ankle are not contacts in the dynamic model. Their solids should be fused conceptually into one leg rigid body.

No knee angle and no ankle angle should exist.

### 7.2 Hip revolute joint

The coaxial cylindrical bearing/pin surfaces define the revolute axis. Continuous contact there is allowed and should not be treated as an impact.

The hip model is therefore:

```text
one revolute coordinate q
with unilateral geometric limits
-20 deg <= q <= 0 deg.
```

### 7.3 Hip hard-stop contacts

For the first dynamics model, use an **ideal hard angular constraint** rather than inventing stop stiffness.

When

```text
q = q_min and qdot tries to decrease
```

or

```text
q = q_max and qdot tries to increase,
```

motion beyond the stop is forbidden.

Later, if measured stop rebound matters, add one experimentally identified impact parameter such as coefficient of restitution `e_stop`, or a measured stop stiffness/damping model. Do not guess these values now.

### 7.4 Foot-ground contact

Foot-ground contact must remain a separate contact problem using the real foot geometry.

A signed gap function should eventually be defined for each foot:

```text
g_i(body_pose, body_roll, q_i) >= 0.
```

- `g_i > 0`: foot airborne
- `g_i = 0`: contact
- attempted `g_i < 0`: forbidden penetration

The existing STEP split-arc Model B remains the correct lateral rocker geometry when a foot is loaded, but walking adds fore-aft foot orientation because the foot is rigidly fixed to the swinging leg.

### Important warning from the fixed-body sweep

If the body is held fixed at the STEP pose and a leg is simply rotated away from `q=0`, the rigid foot numerically penetrates the CAD floor plane. For example the raw fixed-body gap is about `-8.53 mm` at `q=-20 deg`.

This is **not** evidence that the real mechanism is impossible. It means leg swing cannot be simulated independently while body pose is frozen. In walking, body roll/translation unloads and lifts the swing foot. Therefore body pose and foot-ground nonpenetration must be solved together.

## 8. Contact hierarchy recommended for the next simulator

Use the following order:

1. **Rigid assembly constraints**: fuse fixed leg parts.
2. **Hip revolute kinematics**: X-axis rotation only.
3. **Hip hard stops**: exact `[-20, 0] deg` unilateral limits.
4. **Foot-ground geometry**: real foot shape, nonpenetration, contact/lift-off event detection.
5. **Support-state logic**: double support / single support / swing.
6. Only after the above is working, add measured stop impact loss, floor friction/slip, and compliant contact if data require them.

This keeps unmeasured contact parameters from being used to hide geometric mistakes.

## 9. Files added

- `model/leg_kinematics.py`: pure rigid-leg geometry and hard-stop limits
- `analysis/audit_mechanism_kinematics.py`: reproducible STEP axis/boolean-collision audit
- `data/processed/mechanism_audit_summary.json`: recorded result for the supplied STEP
- `data/processed/leg_sweep_collision_keypoints.csv`: key collision/trajectory points around the limits
- `tests/test_leg_kinematics.py`: regression tests for the fixed geometric model

## Current strongest conclusion

The walking-side mechanism should now be modeled as two mirrored, rigid leg+foot bodies, each with exactly one hip DOF:

```text
axis: STEP X
centerline: Y=0, Z=-12 mm
relative angle: -20 deg <= q <= 0 deg
```

The next unresolved kinematic item is not the joint axis anymore. It is the **mapping between STEP Y sign and real walking-forward direction**, followed by coupled body-roll + swing-leg + ground-contact kinematics.
