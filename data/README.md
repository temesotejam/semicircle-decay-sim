# Free-decay audit data

This directory is reserved for event-level data used to reproduce the passive Model A / Model B / empirical-map audit.

Do not copy arbitrary processed outputs here. Each CSV should be traceable to a synchronized RWLOG/video run and should document the extraction source and rule.

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

The V61/V62 historical event tables have not yet been committed to this repository. Until they are added with provenance, RMSE values quoted in documentation are reproduction targets rather than repository-reproducible results.
