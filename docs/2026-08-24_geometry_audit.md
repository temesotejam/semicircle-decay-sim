# 2026-08-24 STEP geometry audit

## Scope

This note checks whether the real foot geometry invalidates the complete-circle assumption used in earlier lateral-energy reasoning.

CAD mass properties are deliberately ignored. Shape only is taken from STEP. Physical mass/CG values come from experiment notes and must remain independently measurable parameters.

## Coordinate-system correspondence

The STEP export contains 10 solids. The two lowest foot solids are mirror images in X and have long extent in Y.

The bottom cylindrical faces have axis direction approximately

```text
(0, 1, 0)
```

so their circular cross-section is in XZ.

Therefore:

```text
CAD X = physical lateral / front-video horizontal
CAD Y = physical fore-aft / rocker rotation axis
CAD Z = physical vertical
lateral sway DOF = rotation about CAD Y
```

The supplied front experiment video visually matches the STEP XZ projection: reaction wheel above the cross member, two lateral legs, and the two separated rocker feet.

Sign convention for left/right should remain explicit in later data import. Geometry is symmetric in X, so sign does not affect the first shape audit.

## Exact foot geometry recovered from STEP

The load-side outer cylindrical faces of both feet are true cylinders with:

```text
radius = 150.000 mm
axis   = Y
center line X = 0
center line Z = 56.951013 mm
```

Their X coverage is:

```text
left foot  : -45 ... -5 mm
right foot :  +5 ... +45 mm
```

Hence the theoretical lowest part of a complete 150 mm circle (`X=0`) is absent.

### Inner missing region

Half gap:

```text
a = 5 mm
```

Full gap:

```text
2a = 10 mm
```

A complete circle would have its lowest point at

```text
Z = 56.951013 - 150 = -93.048987 mm
```

but the lowest existing inner edges are at

```text
Z = -92.965631 mm
```

Difference:

```text
s = R - sqrt(R^2-a^2)
  = 0.083356 mm
```

Although 0.083 mm looks small as a static height, its effect on low-amplitude potential energy is not small because the historical complete-circle model has extremely little height rise near zero.

## Contact-mode boundaries

The tangent point of a complete circle reaches the inner physical edge when

```text
theta_inner = asin(a/R)
            = asin(5/150)
            = 1.910213 deg
```

The outer CAD edge is reached at

```text
theta_outer = asin(45/150)
            = 17.457603 deg
```

Ideal rigid/no-slip interpretation:

```text
theta = 0
    both inner edges are at equal lowest height

0 < |theta| < 1.910 deg
    one inner edge is the support pivot

1.910 <= |theta| <= 17.458 deg
    rolling contact is on the R=150 mm cylindrical arc

|theta| > 17.458 deg
    the nominal tangent lies outside the CAD arc;
    an outer-edge/contact-loss model is needed
```

The ~17.46 deg outer geometric limit is notably close to the independently observed ~17 deg full lift/contact-limit region, but this correspondence should be tested rather than assumed causal.

## Piecewise CG-height model

Use measured upright CG height

```text
H = 120 mm
```

and do not infer CG from CAD density.

For a laterally centered CG, in the inner-edge pivot region:

```text
Delta h(theta)
  = H*(cos(|theta|)-1) + a*sin(|theta|)
```

For the circular-arc region define

```text
hC0 = sqrt(R^2-a^2)
d    = hC0-H
```

then

```text
Delta h(theta)
  = R - d*cos(|theta|) - H
```

The two expressions are continuous at `theta_inner`.

Historical complete-circle approximation:

```text
Delta h_old(theta)
  = (R-H)*(1-cos(theta))
```

## Magnitude of the error around the current gate

Using

```text
R = 150 mm
H = 120 mm
m = 0.1997 kg
```

the comparison is:

| angle | old Delta h | STEP-gap Delta h | old U | STEP-gap U | ratio |
|---:|---:|---:|---:|---:|---:|
| 1.910 deg | 0.0167 mm | 0.1000 mm | 0.0326 mJ | 0.1958 mJ | 6.00x |
| 5.000 deg | 0.1142 mm | 0.1972 mm | 0.2236 mJ | 0.3862 mJ | 1.73x |
| 6.500 deg | 0.1928 mm | 0.2757 mm | 0.3777 mJ | 0.5399 mJ | 1.43x |
| 6.625 deg | 0.2003 mm | 0.2831 mm | 0.3923 mJ | 0.5545 mJ | 1.41x |
| 7.000 deg | 0.2236 mm | 0.3064 mm | 0.4379 mJ | 0.6000 mJ | 1.37x |
| 10.000 deg | 0.4558 mm | 0.5379 mm | 0.8926 mJ | 1.0533 mJ | 1.18x |
| 15.000 deg | 1.0222 mm | 1.1027 mm | 2.0019 mJ | 2.1596 mJ | 1.08x |

The geometry error is therefore disproportionately important at the 6.5--7 deg amplitudes currently used for narrow fixed-Q admission.

## Check against V61 run 2 free-decay data

The aligned V61 run 2 video was used for peak amplitude and the IMU gyro for crossing rate. Only the free-decay section was used for this check; no fixed-Q result is inferred.

A deliberately simple relation was tested per incoming side:

```text
omega_cross ~= sqrt(2*DeltaU(A_prev)/J_side)
```

Only one scalar `J_side` was fitted for each side. This is not yet claimed as the final physical inertia; it is a diagnostic for whether the potential shape is closer to the observed rate-amplitude relation.

### Video peak -> gyro zero-cross rate fit

| previous peak side | complete-circle RMSE | STEP-gap RMSE | reduction |
|---|---:|---:|---:|
| negative | 8.67 deg/s | 3.28 deg/s | 62.1% |
| positive | 4.31 deg/s | 1.60 deg/s | 63.0% |

The same test using the IMU dynamic angle peaks instead of video gives the same direction of improvement.

This is strong evidence that the missing central arc is physically relevant to the observed zero-cross dynamics.

## What this does and does not explain

### It likely explains a significant part of

- why a smooth complete-circle energy model mispredicts zero-cross speed at low amplitude;
- why the 6.5--7 deg region behaves more nonlinear than expected from `(R-H)(1-cos(theta))`;
- why an amplitude-only or smooth-energy interpretation can need apparently inconsistent empirical parameters;
- why a narrow rate gate can be hard to reconcile with an H/C target if the central contact mode is omitted.

### It does NOT yet explain all V61 post-rebuild behavior

Using the free-decay STEP-gap relation as a baseline, V61 positive-arrival rebuild/gate crossings are still systematically faster by about

```text
+9.3 deg/s average
```

while negative-arrival crossings are systematically slower by about

```text
-12.0 deg/s average
```

for comparable immediately preceding peak amplitudes.

A symmetric foot-gap geometry alone cannot produce that directional post-rebuild discrepancy.

Remaining candidates include:

- residual reaction-wheel angular momentum / wheel speed state;
- current decay and motor electrical/mechanical state after a rebuild pulse;
- real lateral CG offset or asymmetric mass distribution;
- side-dependent contact/slip/friction;
- leg/link compliance and configuration;
- estimator timing around the sharp central contact-mode transition.

## Important video caveat

The experiment video shows a white flexible-looking central member between the two black foot arcs. It is not present in STEP as a rigid support solid.

The piecewise gap model assumes this member does not carry significant normal load. If it actually supports the body at the floor, its stiffness/contact profile must be measured and added to the model.

## Immediate simulation plan

1. Implement the piecewise geometry exactly as above.
2. Fit free-decay parameters separately from post-rebuild parameters.
3. Compare complete-circle vs gap geometry against multiple historical free-decay runs.
4. Add an explicit reaction-wheel state (`wheel speed` or equivalent stored angular momentum) before attempting to model the V61 rebuild sequence.
5. Treat contact/slip as a model choice to be tested against video, not assumed no-slip.
