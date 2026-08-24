# 2026-08-24 Post-touchdown support-transfer dynamics screening

## Question

After the swing foot first touches the floor at a nonzero fore-aft angle, does gravity tend to move the mechanism toward a stable flat-sole support, or away from it?

The answer is separated into two stages:

1. **support release in roll**: the reaction wheel must unload the old stance foot, because keeping both feet rigidly fixed overconstrains the 20 deg hip-stop geometry;
2. **fore-aft settling on the new foot**: once the old foot is no longer a fixed support, the new foot can settle from edge contact toward a flat sole.

## Exact geometry condition

Because the ankle is fixed,

```text
beta_foot = alpha_body + q_new
```

where `alpha_body` is body fore-aft pitch and `q_new` is the new leg hip angle. A horizontal sole therefore requires

```text
q_flat = -alpha_body
```

provided `q_flat` lies inside the audited hip stops `[-20, 0] deg`.

Consequences:

- `alpha=0 deg` -> flat at `q=0 deg`;
- `alpha=+5 deg` -> flat at `q=-5 deg`;
- `alpha=-5 deg` -> would need `q=+5 deg`, which is outside the hard stop, so complete flat contact is impossible in that pose.

This directly supports the interpretation that fore-aft body balance is especially important **after first contact**, because it determines whether the new foot can become a true flat support.

## Uniform-density dynamics proxy

A first 1-DOF screening was added after the old foot is assumed unloaded by roll.

Assumptions:

- the first-contact fore/aft edge of the new foot stays fixed on the floor;
- body pitch `alpha` is held fixed;
- the new rigid leg+foot rotates at the hip;
- the old leg is airborne and held at `q_old=-20 deg`;
- every STEP solid has one common density, scaled to the measured total mass `199.7 g`;
- hip friction, floor friction, impact restitution and foot compliance are zero/not modeled.

Thus all energy and time results below are **screening values only**.

## Reference case: about 10 mm geometric step

For `ankle travel = 10 mm`, the audited geometry gives

```text
q_touch = -9.581 deg
```

At `alpha=0 deg`:

```text
q_settle = 0 deg
flat sole reachable = yes
potential change = -9.70 mJ
frictionless proxy settle time = 102.1 ms
pre-flat proxy qdot = +204.0 deg/s
body translation while the contact edge is anchored:
  dY = -14.02 mm
  dZ =  -5.40 mm
```

The negative potential change is the key result: in this proxy the gravitational direction is **from angled first contact toward the flat sole**, not away from it.

For the convenient exact example `q_touch=-10 deg`, the same proxy gives about `-10.02 mJ`, `105.36 ms`, and `207.4 deg/s`.

## Body-pitch sensitivity

For the same 10 mm step:

| body pitch alpha | settle q | flat? | potential change | frictionless proxy time |
|---:|---:|:---:|---:|---:|
| -5 deg | 0 deg | no | -7.41 mJ | 120.8 ms |
| 0 deg | 0 deg | yes | -9.70 mJ | 102.1 ms |
| +2.5 deg | -2.5 deg | yes | -7.59 mJ | 83.0 ms |
| +5 deg | -5 deg | yes | -5.18 mJ | 63.5 ms |
| +10 deg | -10 deg | yes, nearly already flat | -0.28 mJ | 22.8 ms |

The sign convention is the STEP X-axis pitch convention; physical forward/backward sign still needs video/hardware mapping.

## Interpretation of the support exchange

The clearest current mechanism picture is:

```text
1. swing foot first touches on a fore/aft edge
2. reaction-wheel roll continues toward the new-foot side
3. normal load on the old foot decreases and the old foot releases
4. with the old constraint gone, gravity lowers the system around the new-foot edge
5. q_new moves toward q_flat = -alpha
6. the new sole becomes flat if the hard-stop range permits it
7. the former stance leg is now free to become the next swing leg
```

The important point is that steps 2 and 4 are different physical motions:

- **roll (Y-axis)** selects/unloads the support side;
- **fore-aft settling (X-axis)** makes the newly landed foot become a stable flat support.

The reaction wheel is therefore useful not only for choosing touchdown timing, but also for removing the old-foot constraint so the new-foot settling motion can occur.

## Still not identified

A final dynamic support-transfer model still requires:

- actual mass of body/upper leg/lower leg/foot components;
- actual full-system fore-aft CG;
- hip-joint friction;
- foot/floor static and kinetic friction;
- impact restitution / foot structural damping;
- coupling between roll and pitch during the short double-contact phase.

No values for these terms are guessed here.
