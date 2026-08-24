# Free-decay audit data

This directory is reserved for event-level data used to reproduce the passive Model A / Model B / empirical-map audit.

Do not copy arbitrary processed outputs here. Each CSV must be traceable to its source RWLOG, paired video (when present), extraction source, and rule.

## Required event CSV schema

```text
run_id,event_id,prev_peak_side,prev_peak_deg,zero_cross_rate_dps,next_peak_deg
```

- `run_id`: stable run identifier.
- `event_id`: stable half-cycle event identifier within the run.
- `prev_peak_side`: `-1` or `+1`.
- `prev_peak_deg`: previous peak amplitude; signed is preferred.
- `zero_cross_rate_dps`: measured zero-cross angular rate; signed is preferred.
- `next_peak_deg`: next measured peak amplitude. May be blank when only the peak-to-zero-cross audit is available.

## Provenance sidecar

For every `<name>.csv`, add `<name>.json` with at least:

```json
{
  "source_rwlog": "...",
  "source_video": "...",
  "sync_method": "...",
  "peak_source": "video or imu",
  "zero_cross_rate_source": "gyro",
  "event_extraction_revision": "...",
  "q_free_only": true,
  "notes": "..."
}
```

The V61/V62 IMU-only event tables and their provenance are committed here. Historical results using another peak source remain separate metrics until they are regenerated with a versioned extraction rule.

## V61/V62 IMU-only extracted event tables

V61/V62 tables use the extractor `analysis/extract_free_decay_events.py` and contain only consecutive `phase=1` free-decay peak pairs. `prev_peak_deg` and `next_peak_deg` come from `dynamic_hold073` calibration peak events. `zero_cross_rate_dps` is `gyro_pitch_rate_dps`, linearly interpolated at the first `dynamic_hold073` angle sign crossing between those peaks.

These IMU-only V61/V62 tables are a reproducible passive baseline. They are not a substitute for the historical V61 video-peak metric: the sidecar explicitly records the source, hashes, extraction revision, and the fact that the paired video is retained as provenance rather than mixed into the numerical event values.
