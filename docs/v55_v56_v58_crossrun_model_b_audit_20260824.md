# V55/V56/V58 cross-run Model B transfer audit

Date: 2026-08-24

## Scope and reproducibility

This audit uses 54 Q-probe **pre-command** states: all six rows from each of
three V55, three V56, and three V58 runs.  It is an external dynamic
parameter-transfer check, not a passive free-decay experiment.  Pulse,
rebuild, wheel-speed, current, and contact-history effects may remain in each
state.  Consequently, its fitted height is neither a direct measurement of
physical CG height nor a lossless passive model.

The committed event table and sidecar are:

- `data/v55_v56_v58_qprobe_precommand_events.csv`
- `data/v55_v56_v58_qprobe_precommand_events.json`

The sidecar records source-event/metadata SHA-256 values and the fixed
extraction rule.  A row is accepted only when `requested_side == observed_side`,
its bias-corrected rate has that side's sign, and `dynamic_H_prev_deg > 0`.
The state fields are:

```text
arrival_side = requested_side
H_prev        = dynamic_H_prev_deg
rate_zero     = command_rate_bias_corrected_dps
```

A clone can replay the exact audit without local original CSVs:

```powershell
py -m analysis.audit_crossrun_qprobe_prestate `
  --events data/v55_v56_v58_qprobe_precommand_events.csv `
  --out-events audit/replay/events.csv `
  --out-provenance audit/replay/events.json `
  --out-dir audit/replay
```

## Fixed direction-conditioned J_eff,fit transfer

The V61 arrival-side direction-conditioned fitted effective inertias (`J_eff,fit`)
are fixed before fitting Model-B height:

```text
J(-1 arrival) = 0.928e-3 kg m^2
J(+1 arrival) = 0.795e-3 kg m^2
```

Only the STEP Model-B operational effective height `h_eff` is varied for this
fixed-`J_eff,fit` result. It is not treated as a direct physical CG-height
measurement.

| Model-B h_eff | RMSE (deg/s) | bias (deg/s) |
|---|---:|---:|
| 120.000 mm | 7.373 | +6.175 |
| 128.000 mm (standard) | 3.587 | -1.334 |
| 128.345 mm (comparison point) | 3.705 | -1.678 |
| 126.932 mm (all-54 optimum) | 3.425 | -0.281 |

The per-series optima are 127.022 mm (V55), 126.019 mm (V56), and 127.666 mm
(V58).  Across nine individual runs the mean is 126.787 mm, median 126.859 mm,
population standard deviation 1.229 mm, and range 125.176--128.728 mm.

Leave-one-run-out fits remain tightly grouped at 126.584--127.131 mm.  Their
held-run RMSE range is 2.759--4.268 deg/s. This supports using a rounded
`h_eff=128 mm` operating standard, while retaining the uncertainty rather than
claiming an exact physical CG value.

## Model A/B comparison

For this comparison only, each arrival side is fitted with its own effective
inertia on the same 54 states.  Model A is the historical complete circle at
120 mm; Model B is the STEP piecewise rocker at 128.345 mm.

| Model | combined rate RMSE (deg/s) |
|---|---:|
| Model A complete circle | 4.161 |
| Model B STEP geometry | 2.620 |

Model B lowers this in-sample rate RMSE by 37.0%.  The eventwise Model-B
inertia at 128.345 mm has mean 0.815e-3, median 0.812e-3, and sample standard
deviation 0.068e-3 kg m^2.  These descriptive values do not replace the fixed
V61 inertias used in the transfer calculation.

## Decision and physical verification

`RockerGeometry()` now defaults to **`h_eff=128 mm` for Model B**. Historical
Model-A comparisons explicitly pass 120 mm, so the definitions cannot silently
mix. This is an operational effective-height parameter, not a claim that the
physical CG height was measured as 128 mm.
This change does not alter the fixed-Q gate, Q schedule, motor command, or
control implementation.

The next evidence must be physical: a control-free, low-amplitude release test
that spans the 1.910213-degree geometric transition.  Its protocol is in
`docs/low_amplitude_passive_validation_protocol.md`.  Until that test is
performed, 128 mm is an externally supported dynamic operating parameter,
not a confirmed passive rigid-body constant.
