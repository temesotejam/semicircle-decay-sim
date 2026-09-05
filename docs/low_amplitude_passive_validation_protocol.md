# Low-amplitude passive Model-B validation protocol

## Purpose

Test the STEP geometry at the physical contact transition, not the fixed-Q
controller.  The target is the `theta_inner = 1.910213 deg` boundary between
single-inner-edge pivoting and circular-arc rolling.

This protocol follows the V55/V56/V58 cross-run audit.  It is deliberately a
separate experiment because the 54 Q-probe pre-command states did not directly
observe passive contact switching.

## Required measurement mode

Use a dedicated passive logging mode before running this protocol:

- motor driver disabled for the entire recorded interval;
- no excitation pulse, rebuild, cooldown command, fixed-Q probe, or wheel
  command after recording starts;
- record the same IMU/RWLOG angle and gyro rate fields used by
  `analysis.extract_free_decay_events`;
- emit passive peak events compatible with that extractor, or add a separately
  versioned passive extractor before acquiring data;
- record paired video and a visible LED timing trace when available.

The experiment must not reuse a mode that advances into Q-probe control after
free decay.  The low-amplitude release is manual; the firmware is a logger,
not an actuator.

## Acquisition

1. Confirm the mechanism is stable, the travel area is clear, and the motor is
   electrically disabled.  Start RWLOG and video recording.
2. Make one manual release from approximately 3--4 deg on one side.  Do not
   touch the mechanism again until it has settled.
3. Repeat from the opposite side, then repeat the first side.  This gives at
   least three independent decays while avoiding a motor-induced initial state.
4. Preserve each raw RWLOG and video as read-only inputs.  Stop after rest;
   do not enter any Q or rebuild sequence.

The release amplitude is intentionally above 1.91 deg but low enough that the
subsequent decay traverses 3 deg down through the contact boundary toward rest.
No result is accepted if the trace lacks usable samples on both sides of
1.910213 deg.

## Analysis and acceptance

Extract the same event definition used by the V61/V62 audit:

```text
passive peak -> interpolated angle zero crossing -> next passive peak
```

For each run, retain raw samples and classify their geometric mode using
`RockerGeometry.contact_mode`.  Evaluate at minimum:

- continuity of angle/rate through 1.910213 deg;
- residuals of the 128 mm STEP Model B above and below the boundary;
- whether a contact-mode change improves residuals relative to forcing a single
  circular-arc description;
- run/side repeatability of the fitted effective inertia and a separately
  specified loss map;
- RWLOG/video synchronization quality and any manually induced release
  transient before the first accepted passive event.

A useful result is not a single-trace match.  It is a versioned event
set that shows whether the boundary and passive loss behavior are repeatable
across the three releases.  If the boundary is unsupported, the geometry
hypothesis is revised before any V63 or fixed-Q control change.

## Safety boundary

No firmware upload, motor enabling, or physical release is performed merely by
creating this protocol.  Before the first actual run, confirm the surroundings
and the passive-only firmware revision.  The run itself must be recorded in
the workspace change log with its raw-input identities and whether motor
commands were demonstrably absent.
