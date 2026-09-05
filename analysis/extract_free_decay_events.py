#!/usr/bin/env python3
"""Extract fixed-rule passive free-decay events from converted RWLOG artifacts.

Each output row represents one unforced half cycle:
    previous confirmed free-decay peak -> interpolated zero crossing -> next peak

The extractor deliberately uses only phase=1 calibration peak events and rejects
non-alternating peaks, missing zero-cross brackets, or a rate sign inconsistent
with the next peak. Q/rebuild/active phases are never included.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


EXTRACTION_REVISION = "rwlog_free_decay_peak_to_interpolated_zero_cross_v1"


@dataclass(frozen=True)
class Peak:
    peak_index: int
    candidate_peak_ms: float
    peak_side: int
    peak_deg: float


@dataclass(frozen=True)
class Sample:
    t_test_ms: float
    angle_deg: float
    rate_dps: float


@dataclass(frozen=True)
class ZeroCross:
    left_t_test_ms: float
    right_t_test_ms: float
    t_test_ms: float
    rate_dps: float
    fraction: float


def sign(value: float) -> int:
    if value > 0.0:
        return 1
    if value < 0.0:
        return -1
    return 0


def load_free_decay_peaks(metadata_path: Path) -> list[Peak]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    rows = metadata.get("calibration_peak_events")
    if not isinstance(rows, list):
        raise ValueError("metadata has no calibration_peak_events array")

    peaks: list[Peak] = []
    for row in rows:
        if int(row["phase"]) != 1:
            continue
        peak = Peak(
            peak_index=int(row["peak_index"]),
            candidate_peak_ms=float(row["candidate_peak_ms"]),
            peak_side=int(row["peak_side"]),
            peak_deg=float(row["peak_signed_dynamic_hold073_deg"]),
        )
        if sign(peak.peak_deg) != peak.peak_side:
            raise ValueError(
                f"peak {peak.peak_index}: signed amplitude and peak_side disagree"
            )
        peaks.append(peak)

    peaks.sort(key=lambda item: (item.candidate_peak_ms, item.peak_index))
    if len(peaks) < 3:
        raise ValueError("at least three phase=1 free-decay peaks are required")
    return peaks


def load_samples(timeseries_path: Path) -> list[Sample]:
    required = {
        "t_test_ms",
        "pitch_dynamic_hold073_deg",
        "gyro_pitch_rate_dps",
    }
    with timeseries_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"timeseries missing required columns: {sorted(missing)}")
        samples = [
            Sample(
                t_test_ms=float(row["t_test_ms"]),
                angle_deg=float(row["pitch_dynamic_hold073_deg"]),
                rate_dps=float(row["gyro_pitch_rate_dps"]),
            )
            for row in reader
        ]

    samples.sort(key=lambda item: item.t_test_ms)
    if len(samples) < 2:
        raise ValueError("at least two timeseries samples are required")
    return samples


def interpolate_zero_cross(
    samples: Iterable[Sample],
    prev_peak: Peak,
    next_peak: Peak,
) -> ZeroCross:
    expected_left_sign = prev_peak.peak_side
    expected_right_sign = next_peak.peak_side
    if expected_left_sign == expected_right_sign:
        raise ValueError(
            f"peaks {prev_peak.peak_index}->{next_peak.peak_index} do not alternate"
        )

    window = [
        sample
        for sample in samples
        if prev_peak.candidate_peak_ms <= sample.t_test_ms <= next_peak.candidate_peak_ms
    ]
    for left, right in zip(window, window[1:]):
        if sign(left.angle_deg) != expected_left_sign:
            continue
        if sign(right.angle_deg) != expected_right_sign:
            continue
        denominator = abs(left.angle_deg) + abs(right.angle_deg)
        if denominator <= 0.0:
            continue
        fraction = abs(left.angle_deg) / denominator
        rate = left.rate_dps + fraction * (right.rate_dps - left.rate_dps)
        if sign(rate) != expected_right_sign:
            raise ValueError(
                f"zero-cross rate sign {rate} disagrees with next peak side "
                f"for peaks {prev_peak.peak_index}->{next_peak.peak_index}"
            )
        return ZeroCross(
            left_t_test_ms=left.t_test_ms,
            right_t_test_ms=right.t_test_ms,
            t_test_ms=left.t_test_ms + fraction * (right.t_test_ms - left.t_test_ms),
            rate_dps=rate,
            fraction=fraction,
        )

    raise ValueError(
        f"no valid dynamic_hold073 sign-change bracket for "
        f"peaks {prev_peak.peak_index}->{next_peak.peak_index}"
    )


def extract_events(
    peaks: list[Peak],
    samples: list[Sample],
    run_id: str,
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for prev_peak, next_peak in zip(peaks, peaks[1:]):
        cross = interpolate_zero_cross(samples, prev_peak, next_peak)
        events.append(
            {
                "run_id": run_id,
                "event_id": (
                    f"free_peak_{prev_peak.peak_index}_to_{next_peak.peak_index}"
                ),
                "prev_peak_side": prev_peak.peak_side,
                "prev_peak_deg": prev_peak.peak_deg,
                "zero_cross_rate_dps": cross.rate_dps,
                "next_peak_deg": next_peak.peak_deg,
                "prev_peak_candidate_ms": prev_peak.candidate_peak_ms,
                "next_peak_candidate_ms": next_peak.candidate_peak_ms,
                "zero_cross_left_sample_ms": cross.left_t_test_ms,
                "zero_cross_right_sample_ms": cross.right_t_test_ms,
                "zero_cross_interpolated_ms": cross.t_test_ms,
                "zero_cross_linear_fraction": cross.fraction,
                "peak_source": "rwlog_calibration_peak_events.dynamic_hold073",
                "zero_cross_rate_source": (
                    "rwlog_timeseries.gyro_pitch_rate_dps_linear_interpolated_at_"
                    "dynamic_hold073_angle_zero"
                ),
            }
        )
    return events


def artifact_identity(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "basename": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest().upper(),
    }


def write_csv(path: Path, events: list[dict[str, object]]) -> None:
    fields = [
        "run_id",
        "event_id",
        "prev_peak_side",
        "prev_peak_deg",
        "zero_cross_rate_dps",
        "next_peak_deg",
        "prev_peak_candidate_ms",
        "next_peak_candidate_ms",
        "zero_cross_left_sample_ms",
        "zero_cross_right_sample_ms",
        "zero_cross_interpolated_ms",
        "zero_cross_linear_fraction",
        "peak_source",
        "zero_cross_rate_source",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(events)


def write_provenance(
    path: Path,
    *,
    run_id: str,
    metadata_path: Path,
    timeseries_path: Path,
    source_rwlog: Path,
    source_video: Path,
    events: list[dict[str, object]],
) -> None:
    sidecar: dict[str, Any] = {
        "run_id": run_id,
        "source_rwlog": artifact_identity(source_rwlog),
        "source_video": artifact_identity(source_video),
        "converted_rwlog_metadata": artifact_identity(metadata_path),
        "converted_rwlog_timeseries": artifact_identity(timeseries_path),
        "sync_method": (
            "Numerical extraction is RWLOG-internal (no cross-device synchronization); "
            "the paired video is retained in provenance only, and its angle values are not "
            "mixed into this IMU-only event table."
        ),
        "peak_source": (
            "calibration_peak_events with phase=1, using "
            "peak_signed_dynamic_hold073_deg at candidate_peak_ms"
        ),
        "zero_cross_rate_source": (
            "gyro_pitch_rate_dps linearly interpolated across the first "
            "pitch_dynamic_hold073_deg sign-change bracket between each "
            "consecutive free-decay peak pair"
        ),
        "event_extraction_revision": EXTRACTION_REVISION,
        "q_free_only": True,
        "selection_rule": (
            "use every consecutive phase=1 peak pair only; require alternating "
            "peak sides, an angle-sign-change bracket inside the candidate-peak "
            "time window, and rate sign equal to the next peak side; reject "
            "rather than silently substitute nearest samples"
        ),
        "event_count": len(events),
        "event_time_bounds_ms": {
            "first_prev_peak": events[0]["prev_peak_candidate_ms"],
            "last_next_peak": events[-1]["next_peak_candidate_ms"],
        },
        "notes": (
            "Initial excitation precedes this segment but is excluded. This "
            "table is passive free-decay after the final initial-build-up peak; "
            "it is not a Q-probe or post-rebuild table."
        ),
    }
    path.write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--timeseries", type=Path, required=True)
    parser.add_argument("--source-rwlog", type=Path, required=True)
    parser.add_argument("--source-video", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-provenance", type=Path, required=True)
    args = parser.parse_args()

    peaks = load_free_decay_peaks(args.metadata)
    samples = load_samples(args.timeseries)
    events = extract_events(peaks, samples, args.run_id)

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_provenance.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_csv, events)
    write_provenance(
        args.out_provenance,
        run_id=args.run_id,
        metadata_path=args.metadata,
        timeseries_path=args.timeseries,
        source_rwlog=args.source_rwlog,
        source_video=args.source_video,
        events=events,
    )
    print(
        json.dumps(
            {
                "run_id": args.run_id,
                "events": len(events),
                "out_csv": str(args.out_csv),
                "out_provenance": str(args.out_provenance),
                "event_extraction_revision": EXTRACTION_REVISION,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
