# 2026-08-24 CG-height identification from V61 run 2

## Goal

Estimate the upright CG height `H` after fixing the STEP-derived split-arc geometry:

- `R = 150 mm`
- inner arc edge `a = 5 mm`
- central gap `10 mm`
- rigid Model B contact geometry

CAD mass properties are **not** used.

## Identification idea

At a free-decay peak, the rigid Model-B gravitational potential rise is `U_B(A; H)`.  The zero-cross speed is modeled as

`|omega_zero| ~= beta_side * sqrt(U_B(A; H))`.

A separate `beta_side` is fitted for each travel direction, so effective inertia and approximately direction-specific loss are absorbed by scale.  The CG height is identified from the **shape of zero-cross speed versus peak amplitude**, not from an assumed inertia value.

This is preferable to fitting peak-to-zero time at this stage because the current rigid time-domain model does not reproduce the strong amplitude dependence of the measured quarter-cycle time; using those times biases `H` through unmodeled contact/loss dynamics.

## Gyro result

Using 11 passive V61 run-2 peak-to-zero transitions:

- best common `H = 128.345 mm`
- rate RMSE = `2.256 deg/s`
- leave-one-transition-out range: `124.344 .. 132.442 mm`

Separate-side fits give roughly:

- negative peak -> positive travel: `H = 129.264 mm`
- positive peak -> negative travel: `H = 125.204 mm`

The physical CG height should be common; the difference is interpreted as remaining side asymmetry/loss/model error rather than two different CG heights.

## Independent video-rate cross-check

The synchronized video angle was locally fit with a cubic polynomial around each zero crossing (`+/-0.08 s`) and differentiated at the crossing.  Repeating the same amplitude-speed-shape fit gives:

- best common `H = 127.355 mm`
- rate RMSE = `2.004 deg/s`
- leave-one-transition-out range: `122.346 .. 131.558 mm`

Changing the local video fit window from about `0.06` to `0.14 s` keeps the common estimate approximately in the `127 .. 130 mm` range.

Thus gyro and video independently support nearly the same CG-height estimate even though their absolute zero-cross speeds differ by several deg/s.

## Recommended value

For the current rigid Model-B baseline use

`H = 0.128 m`

with a current practical uncertainty band of about

`H = 0.128 +/- 0.004 m`

for this session/model.

This replaces `H = 0.120 m` as the **dynamic Model-B working value**, but it should still be checked by a new static CG measurement before being called the final physical CG height.

With `H = 128.345 mm`, the circle-center-to-CG distance is

`d = sqrt(R^2-a^2) - H = 21.571 mm`.

The previous `H = 120 mm` assumption gave `d = 29.917 mm`, so the gravity lever arm changes by about 28%.

## Why timing-based estimates are not adopted

Several alternative fits that force the present rigid model to explain peak-to-zero time produce materially different H values.  The reason is diagnostic: the measured peak-to-zero time shortens strongly as amplitude decays, whereas the current lossless rigid model predicts a much weaker dependence and can push inertia parameters to nonphysical boundaries.

Therefore quarter-cycle time is presently evidence that the time-domain contact/loss model is incomplete, not a clean CG-height observable.

## Consequence for the old effective inertia

Changing H also changes the scale required to match zero-cross speed.  With gyro zero-cross rates and `H = 128.345 mm`, the simple direction-wise energy scale corresponds approximately to:

- negative peak -> positive travel: `J_eff ~= 0.795e-3 kg m^2`
- positive peak -> negative travel: `J_eff ~= 0.928e-3 kg m^2`

These are **effective energy-fit parameters**, not the rigid-body `I_G`; they still absorb loss and model reduction.  They should be re-identified after the time-domain loss/contact model is completed.

## Current status

The strongest current statement is:

**Dynamic free-decay data support `H ~= 128 mm` for Model B, with a practical current range roughly 124--132 mm.**

Next validation should repeat the passive decay experiment and independently remeasure the static CG height.
