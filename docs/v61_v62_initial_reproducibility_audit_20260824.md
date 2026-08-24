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

The four event tables contain 11 accepted half cycles each (44 total). Their source RWLOG/video identities and converted-input hashes are recorded in their adjacent JSON sidecars. Numerical peak/rate extraction is RWLOG-internal; the paired video is provenance only and is not mixed into these IMU tables.

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

| Run | Model A RMSE | Model B RMSE | Model A LOOCV | Model B LOOCV |
|---|---:|---:|---:|---:|
| V61 run 1 (102479546) | 8.675 | 4.710 | 11.313 | 6.069 |
| V61 run 2 (156491989) | 6.866 | 3.125 | 8.629 | 3.961 |
| V62 run 1 (58517125) | 7.777 | 4.071 | 9.946 | 5.259 |
| V62 run 2 (107933178) | 6.071 | 3.046 | 7.675 | 3.740 |

STEP Model B improves both in-sample and leave-one-out RMSE in every one of the four fixed event sets. This establishes a reproducible IMU-only baseline for that comparison.

## Effective inertia and geometry limits

The fitted Model B effective inertias (negative/positive previous-peak side) are:

| Run | J_eff negative (kg m^2) | J_eff positive (kg m^2) |
|---|---:|---:|
| V61 run 1 | 0.000993 | 0.001510 |
| V61 run 2 | 0.001068 | 0.001450 |
| V62 run 1 | 0.001157 | 0.001278 |
| V62 run 2 | 0.001088 | 0.001407 |

They remain side-asymmetric and vary between runs. The present data therefore supports separate run/side fits, but does not yet establish a single reproducible constant J_eff. Amplitude-dependent inertia and/or loss should remain open hypotheses.

The fixed STEP geometry uses R=150 mm, a 10 mm central gap, inner boundary 1.910213 degrees, and outer boundary 17.457603 degrees. All 44 accepted events have geometric mode `circular_arc`; their previous-peak absolute amplitudes are 4.00--14.27 degrees. Consequently this dataset does **not** directly validate the real contact transition near 1.91 degrees. That boundary remains a geometry-derived hypothesis requiring dedicated low-amplitude free-decay data.

## Empirical map and historical numbers

The empirical map predicts next-peak amplitude, so its RMSE unit is degrees and it must not be ranked numerically against the A/B rate RMSEs. Its support limits and LOOCV selection are retained in each `summary.json`; it is never extrapolated.

The previously recorded V61 figures that mixed video-derived peak angles with IMU rate are not claimed to be reproduced by this audit. This audit deliberately fixes both peak and rate quantities to the RWLOG IMU. A future cross-sensor audit can use a separately versioned video-angle extraction rule and compare it against this baseline without conflating the metrics.

## Decision

Step 1 is complete for the four locally available V61/V62 primary runs: fixed-rule event data, provenance, per-event predictions, and regenerated summaries are now versioned. No conclusion about Q reproducibility is justified from this passive-model audit alone. Before any V63 control change, collect low-amplitude free-decay data that crosses the 1.91-degree region and use the same extractor to test the contact boundary and J_eff/loss repeatability.
