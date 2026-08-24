# Initial V61/V62 Model B reproducibility audit

Date: 2026-08-24
Scope: passive free decay only; this audit does not alter firmware, H/C/rate gates, Q values, Q selection, or motor commands.

## Fixed event definition

Every data row is exactly one unforced half cycle:

```text
previous phase=1 peak -> interpolated dynamic-hold angle zero crossing -> next phase=1 peak
```

The peak angle comes from the converted RWLOG's `calibration_peak_events` entry with `phase=1`. The zero-cross angular rate is `gyro_pitch_rate_dps`, linearly interpolated at the first `pitch_dynamic_hold073_deg` sign-change bracket between those two peaks.

The extractor rejects a pair unless the peak sides alternate and the interpolated rate has the sign of the next peak. The output therefore contains no initial excitation, rebuild, Q-probe, cooldown, or active-control events.

The four event tables contain 11 accepted half cycles each (44 total). Their source
RWLOG/video identities and converted-input hashes are recorded in adjacent JSON
sidecars. Historical `V62_stategen_run_1` and `V62_stategen_run_2` below refer to
state-generation/free-decay source runs only; no `V62_fixedQ_run` is represented by
this audit. Numerical peak/rate extraction is RWLOG-internal; paired video is provenance only.

## Reproduce

From repository root:

```powershell
py -m analysis.audit_free_decay data/v61_run1_102479546_imu_free_decay_events.csv --out-dir audit/v61_run1_102479546_imu_free_decay
py -m analysis.audit_free_decay data/v61_run2_156491989_imu_free_decay_events.csv --out-dir audit/v61_run2_156491989_imu_free_decay
py -m analysis.audit_free_decay data/v62_run1_58517125_imu_free_decay_events.csv --out-dir audit/v62_run1_58517125_imu_free_decay
py -m analysis.audit_free_decay data/v62_run2_107933178_imu_free_decay_events.csv --out-dir audit/v62_run2_107933178_imu_free_decay
```

`summary.json` reports Model A/B and empirical-map fits. `event_predictions.csv` records every prediction, residual, and geometric contact mode.

## Model A/B result

Model A and Model B both predict zero-cross angular rate; the figures below are combined left/right RMSE in deg/s.
Model A is fixed at its historical complete-circle height of 120 mm. Model B
uses `h_eff=128 mm`, an externally supported STEP operational effective height;
it is not a direct measurement of physical CG height. The two model parameters
are therefore no longer silently shared.

| Run | Model A RMSE | Model B RMSE | Model A LOOCV | Model B LOOCV |
|---|---:|---:|---:|---:|
| V61 run 1 (102479546) | 8.675 | 4.158 | 11.313 | 5.214 |
| V61 run 2 (156491989) | 6.866 | 2.647 | 8.629 | 3.215 |
| V62_stategen_run_1 (58517125) | 7.777 | 3.308 | 9.946 | 4.206 |
| V62_stategen_run_2 (107933178) | 6.071 | 2.931 | 7.675 | 3.421 |

STEP Model B improves both in-sample and leave-one-out RMSE in every one of the four fixed event sets. This establishes a reproducible IMU-only baseline for that comparison.

## Direction-conditioned fitted effective inertia and geometry limits

The fitted Model B direction-conditioned effective inertias (`J_eff,fit`,
negative/positive previous-peak side) are:

| Run | J_eff,fit negative (kg m^2) | J_eff,fit positive (kg m^2) |
|---|---:|---:|
| V61 run 1 | 0.000785 | 0.001171 |
| V61 run 2 | 0.000839 | 0.001122 |
| V62_stategen_run_1 | 0.000900 | 0.000991 |
| V62_stategen_run_2 | 0.000849 | 0.001086 |

They remain side-asymmetric and vary between runs. They are fitted effective
parameters, not measured rigid-body inertias. The present data therefore supports
separate run/side `J_eff,fit` values, but does not yet establish a single
reproducible constant. Amplitude-dependent inertia and/or loss remain open hypotheses.

The fixed STEP geometry uses R=150 mm, a 10 mm central gap, inner boundary 1.910213 degrees, and outer boundary 17.457603 degrees. All 44 accepted events have geometric mode `circular_arc`; their previous-peak absolute amplitudes are 4.00--14.27 degrees. Consequently this dataset does **not** directly validate the real contact transition near 1.91 degrees. That boundary remains a geometry-derived hypothesis requiring dedicated low-amplitude free-decay data.

## Empirical map and historical numbers

The empirical map predicts next-peak amplitude, so its RMSE unit is degrees and it must not be ranked numerically against the A/B rate RMSEs. Its support limits and LOOCV selection are retained in each `summary.json`; it is never extrapolated.

The previously recorded V61 figures that mixed video-derived peak angles with IMU rate are not claimed to be reproduced by this audit. This audit deliberately fixes both peak and rate quantities to the RWLOG IMU. A future cross-sensor audit can use a separately versioned video-angle extraction rule and compare it against this baseline without conflating the metrics.

## Decision

Step 1 is complete for the four locally available V61/V62 primary runs: fixed-rule event data, provenance, per-event predictions, and regenerated summaries are now versioned. No conclusion about Q reproducibility is justified from this passive-model audit alone. Before any V63 control change, collect low-amplitude free-decay data that crosses the 1.91-degree region and use the same extractor to test the contact boundary and J_eff/loss repeatability.

The independent V55/V56/V58 external transfer audit is documented in
`docs/v55_v56_v58_crossrun_model_b_audit_20260824.md`. It supports
`h_eff=128 mm` as the Model-B operating standard, but does not replace this
required passive test.
