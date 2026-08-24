# Post-touchdown support transfer and sole settling

## Current gap in the motion explorer

The original motion explorer stopped at **first possible floor contact**.  It did not yet model the phase that the real mechanism needs next:

1. swing foot touches at an unstable fore-aft edge angle,
2. reaction-wheel roll continues to unload the old stance foot,
3. the new foot/leg settles toward a longitudinally flat sole,
4. the old stance foot releases and becomes the next swing leg.

This note adds a geometry-first model for that phase without inventing contact stiffness, damping, restitution, or friction.

## Exact flat-sole condition

The hip and ankle both use/follow the STEP X-axis rotation.  The ankle is fixed, so if

- `alpha` = body fore-aft pitch about STEP X,
- `q` = leg angle relative to the body,

then the absolute fore-aft foot pitch is

```text
beta_foot = alpha + q
```

The longitudinal sole is flat on a horizontal floor when

```text
beta_foot = 0
```

therefore

```text
q_flat = -alpha
```

with the mechanical constraint

```text
-20 deg <= q <= 0 deg.
```

This gives a direct role to the body's fore-aft balance.  For example:

- `alpha = 0 deg` -> flat support requires `q = 0 deg`.
- `alpha = +5 deg` -> flat support requires `q = -5 deg` and is geometrically feasible.
- `alpha = -5 deg` -> flat support would require `q = +5 deg`, which is outside the CAD hard stop; if the body stays at that pitch, a perfectly flat longitudinal sole cannot be reached.

The physical sign of STEP fore-aft pitch versus walking-forward is not yet mapped, so positive/negative pitch must not yet be called forward/backward lean.

## What must happen after first contact

At zero body pitch, an early touchdown around `q=-10 deg` means the new foot first contacts while its longitudinal sole is still about `-10 deg` from horizontal.  It is therefore an edge-contact state, not a stable full-sole state.

To become the new stance foot it must move toward `q=0 deg` while the old stance foot loses support.

This is not achievable by simply freezing the old support and rotating the new leg.  A no-slip two-contact screening showed that keeping both initial contact material points fixed would immediately require the old leg to move past its `q=0` hard stop (e.g. about `+1.4 deg` when the new leg has only settled from `-10` to `-8.75 deg`) and the old foot geometry would penetrate the floor.  Therefore the real transfer must include at least one of:

- old-foot peeling/lift-off,
- old-foot fore-aft slip while nearly unloaded,
- change of lateral rocker contact as roll continues,
- compliance in the feet/contact.

That is an important result: **first contact is not support exchange.  The reaction wheel must continue the lateral load transfer so the old support constraint can be released.**

## Geometry-only settling path

A useful quasi-static limiting path is:

- preserve the new foot's first-contact edge point (no-slip new contact),
- let the new leg move from `q_touch` toward the reachable flat target,
- reduce roll from the first-contact boundary toward the new-support side,
- allow the old foot to unload/release instead of forcing it to remain a fixed full contact.

For the representative `alpha=0`, `q_touch=-10 deg`, old stance `q=0 deg` case, the equal-height contact boundary is:

| new q | roll boundary | STEP-Y shift needed to keep the new contact edge fixed | uniform-STEP proxy CG height |
|---:|---:|---:|---:|
| -10.00 | +13.548 deg | 0.000 mm | 104.997 mm |
| -8.75 | +12.776 deg | -1.882 mm | 104.903 mm |
| -7.50 | +11.894 deg | -3.752 mm | 104.802 mm |
| -5.00 | +9.695 deg | -7.450 mm | 104.580 mm |
| -2.50 | +6.527 deg | -11.086 mm | 104.340 mm |
| 0.00 | 0.000 deg | -14.655 mm | 104.089 mm |

The CG-height column uses **uniform STEP density only**.  It is not the physical CG model.  Its only current use is a direction screening: along this released-old-foot path the proxy potential decreases as the new foot settles from the tilted edge contact to the flat longitudinal sole.

The STEP-Y shift is also not yet the final laboratory-frame walking displacement because the physical `+Y` walking sign and the exact old-foot slip/lift path are not yet measured.

## Local edge-pivot gravity check

For a fixed first-contact pivot, the gravity moment arm can be screened from the contact Y coordinate and system CG Y coordinate.  In the zero-pitch, old-stance `q=0` uniform-STEP proxy:

- `q_touch=-10 deg`: local flattening margin about `+9.84 mm`.
- `q_touch=-15 deg`: about `+2.67 mm`.
- `q_touch=-17.5 deg`: about `-0.96 mm`.
- `q_touch=-20 deg`: about `-4.61 mm`.

Positive means a *rigid single-pivot* gravity moment has the sign that flattens the foot.  This is deliberately labeled a **local screening metric**, not the complete generalized torque, because the real mechanism has a free hip joint and a moving/releasing old support.  The no-slip settling path can still lower total potential even where this local rigid-pivot metric changes sign.

## Current support-transfer simulation state

The next visualization therefore uses the following sequence:

```text
first edge contact
    -> continue RW roll / unload old support
    -> release old foot constraint
    -> new q moves toward q_flat = -alpha
    -> longitudinal sole becomes flat if q_flat lies in [-20,0]
    -> old foot becomes the next swing foot
```

This is a **quasi-static kinematic/support-state animation**, not yet a time-accurate impact/contact simulation.

## Still required for a physical dynamic simulation

- actual body / left leg / right leg masses and fore-aft CG locations,
- hip joint friction,
- foot-ground static/dynamic friction,
- foot/contact compliance and hysteresis,
- impact restitution / damping,
- measured body fore-aft pitch during a real support exchange,
- actual old-foot lift/slip trajectory,
- synchronized side-view video for `q_left`, `q_right`, and body pitch.

Once those are measured, the same state machine can be upgraded from quasi-static geometry to a constrained multibody dynamic model.
