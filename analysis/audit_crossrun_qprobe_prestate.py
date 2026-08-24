"""Reproduce the V55/V56/V58 Model-B height transfer audit.

The input states are Q-probe *pre-command* samples, not passive free decay.
They are used only for external parameter transfer: fixed V61 arrival-side
effective inertias plus one common STEP geometry height are assessed on the
same 54 recorded states.  The source CSVs are never modified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from dataclasses import asdict, dataclass
from math import degrees, radians, sqrt
from pathlib import Path

from model.rocker_geometry import RockerGeometry


MASS_KG = 0.1997
FIXED_V61_DIRECTION_CONDITIONED_J_EFF_FIT_BY_ARRIVAL_SIDE = {
    -1: 0.928e-3,
    +1: 0.795e-3,
}
HISTORICAL_MODEL_A_HEIGHT_M = 0.120
STANDARD_MODEL_B_HEIGHT_M = 0.128


@dataclass(frozen=True)
class Event:
    series: str
    run_id: str
    source_probe_index: int
    q_probe_schedule_id: int
    planned_probe_index: int
    q_target_mA_s: float
    q_effective_mA_s: float
    arrival_side: int
    h_prev_deg: float
    zero_cross_rate_dps: float


@dataclass(frozen=True)
class Source:
    series: str
    run_id: str
    event_csv: Path
    metadata_json: Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_source(raw: str) -> Source:
    parts = raw.split("|", 3)
    if len(parts) != 4:
        raise ValueError("--source must be SERIES|RUN|EVENT_CSV|METADATA_JSON")
    series, run_id, event_csv, metadata_json = parts
    return Source(series, run_id, Path(event_csv), Path(metadata_json))


def as_side(raw: str, field: str) -> int:
    value = int(raw)
    if value not in (-1, +1):
        raise ValueError(f"{field} must be -1 or +1, got {raw!r}")
    return value


def load_source(source: Source) -> tuple[list[Event], dict[str, object]]:
    if not source.event_csv.is_file() or not source.metadata_json.is_file():
        raise ValueError(f"missing source for {source.series}/{source.run_id}")
    with source.event_csv.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    required = {
        "probe_index", "q_probe_schedule_id", "planned_probe_index",
        "q_target_mA_s", "q_effective_mA_s", "requested_side",
        "observed_side", "dynamic_H_prev_deg",
        "command_rate_bias_corrected_dps",
    }
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"{source.event_csv}: missing columns {sorted(missing)}")

    events: list[Event] = []
    for row in rows:
        requested = as_side(row["requested_side"], "requested_side")
        observed = as_side(row["observed_side"], "observed_side")
        rate = float(row["command_rate_bias_corrected_dps"])
        h_prev = float(row["dynamic_H_prev_deg"])
        if requested != observed:
            raise ValueError(f"{source.series}/{source.run_id}: side mismatch")
        if rate * requested <= 0.0:
            raise ValueError(f"{source.series}/{source.run_id}: rate-side mismatch")
        if not h_prev > 0.0:
            raise ValueError(f"{source.series}/{source.run_id}: non-positive H_prev")
        events.append(Event(
            series=source.series, run_id=source.run_id,
            source_probe_index=int(row["probe_index"]),
            q_probe_schedule_id=int(row["q_probe_schedule_id"]),
            planned_probe_index=int(row["planned_probe_index"]),
            q_target_mA_s=float(row["q_target_mA_s"]),
            q_effective_mA_s=float(row["q_effective_mA_s"]),
            arrival_side=requested, h_prev_deg=h_prev,
            zero_cross_rate_dps=rate,
        ))

    meta = json.loads(source.metadata_json.read_text(encoding="utf-8"))
    provenance = {
        "series": source.series,
        "run_id": source.run_id,
        "event_csv_filename": source.event_csv.name,
        "event_csv_sha256": sha256_file(source.event_csv),
        "metadata_filename": source.metadata_json.name,
        "metadata_sha256": sha256_file(source.metadata_json),
        "metadata_identity": {
            key: meta[key] for key in (
                "format", "format_version", "calibration_algorithm_revision",
                "firmware_revision",
            ) if key in meta
        },
        "n_events": len(events),
    }
    return events, provenance


def load_sources(raw_sources: list[str]) -> tuple[list[Event], list[dict[str, object]]]:
    events: list[Event] = []
    provenance: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_sources:
        source = parse_source(raw)
        key = (source.series, source.run_id)
        if key in seen:
            raise ValueError(f"duplicate source {key}")
        seen.add(key)
        source_events, source_provenance = load_source(source)
        events.extend(source_events)
        provenance.append(source_provenance)
    if not events:
        raise ValueError("no events")
    return events, provenance



def read_event_table(path: Path) -> list[Event]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    required = set(Event.__dataclass_fields__)
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    return [
        Event(
            series=row["series"], run_id=row["run_id"],
            source_probe_index=int(row["source_probe_index"]),
            q_probe_schedule_id=int(row["q_probe_schedule_id"]),
            planned_probe_index=int(row["planned_probe_index"]),
            q_target_mA_s=float(row["q_target_mA_s"]),
            q_effective_mA_s=float(row["q_effective_mA_s"]),
            arrival_side=as_side(row["arrival_side"], "arrival_side"),
            h_prev_deg=float(row["h_prev_deg"]),
            zero_cross_rate_dps=float(row["zero_cross_rate_dps"]),
        )
        for row in rows
    ]

def predicted_rate_dps(event: Event, height_m: float, inertia_kg_m2: float) -> float:
    geom = RockerGeometry(cg_height_upright_m=height_m)
    potential = geom.potential_delta_j(radians(event.h_prev_deg), MASS_KG)
    return degrees(sqrt(2.0 * potential / inertia_kg_m2))


def residual_dps(event: Event, height_m: float, inertia_kg_m2: float) -> float:
    return predicted_rate_dps(event, height_m, inertia_kg_m2) - abs(event.zero_cross_rate_dps)


def rmse(values: list[float]) -> float:
    return sqrt(sum(value * value for value in values) / len(values))


def fixed_inertia_residuals(events: list[Event], height_m: float) -> list[float]:
    return [
        residual_dps(
            e,
            height_m,
            FIXED_V61_DIRECTION_CONDITIONED_J_EFF_FIT_BY_ARRIVAL_SIDE[e.arrival_side],
        )
        for e in events
    ]


def fixed_inertia_summary(events: list[Event], height_m: float) -> dict[str, float | int]:
    errors = fixed_inertia_residuals(events, height_m)
    return {
        "height_m": height_m,
        "n_events": len(events),
        "rmse_dps": rmse(errors),
        "bias_dps": statistics.fmean(errors),
    }


def fit_height_m(events: list[Event], low_m: float = 0.110, high_m: float = 0.140) -> float:
    """Bounded golden-section fit with fixed V61 arrival-side inertia."""
    phi = (1.0 + sqrt(5.0)) / 2.0
    low, high = low_m, high_m
    for _ in range(100):
        c = high - (high - low) / phi
        d = low + (high - low) / phi
        if rmse(fixed_inertia_residuals(events, c)) <= rmse(fixed_inertia_residuals(events, d)):
            high = d
        else:
            low = c
    return (low + high) / 2.0


def by_key(events: list[Event], key: str) -> dict[str, list[Event]]:
    groups: dict[str, list[Event]] = {}
    for event in events:
        value = str(getattr(event, key))
        groups.setdefault(value, []).append(event)
    return groups


def height_fits(events: list[Event], key: str) -> dict[str, dict[str, float | int]]:
    output: dict[str, dict[str, float | int]] = {}
    for group, group_events in sorted(by_key(events, key).items()):
        height_m = fit_height_m(group_events)
        output[group] = fixed_inertia_summary(group_events, height_m)
    return output


def leave_one_run_out(events: list[Event]) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for run_id, held in sorted(by_key(events, "run_id").items()):
        train = [event for event in events if event.run_id != run_id]
        height_m = fit_height_m(train)
        summary = fixed_inertia_summary(held, height_m)
        summary["fit_height_m"] = height_m
        result[run_id] = summary
    return result


def potential_j(event: Event, height_m: float, complete_circle: bool) -> float:
    geom = RockerGeometry(cg_height_upright_m=height_m)
    angle = radians(event.h_prev_deg)
    if complete_circle:
        return geom.complete_circle_potential_delta_j(angle, MASS_KG)
    return geom.potential_delta_j(angle, MASS_KG)


def fit_effective_inertia(events: list[Event], height_m: float, complete_circle: bool) -> float:
    x = [sqrt(2.0 * potential_j(event, height_m, complete_circle)) for event in events]
    y = [radians(abs(event.zero_cross_rate_dps)) for event in events]
    scale = sum(a * b for a, b in zip(x, y)) / sum(a * a for a in x)
    return 1.0 / (scale * scale)


def flexible_model_summary(
    events: list[Event], height_m: float, complete_circle: bool,
) -> dict[str, object]:
    by_side: dict[str, dict[str, float | int]] = {}
    all_errors: list[float] = []
    for side in (-1, +1):
        side_events = [event for event in events if event.arrival_side == side]
        inertia = fit_effective_inertia(side_events, height_m, complete_circle)
        errors = [
            degrees(sqrt(2.0 * potential_j(event, height_m, complete_circle) / inertia))
            - abs(event.zero_cross_rate_dps)
            for event in side_events
        ]
        all_errors.extend(errors)
        by_side[str(side)] = {
            "n_events": len(side_events),
            "J_eff_fit_kg_m2": inertia,
            "rmse_dps": rmse(errors),
            "bias_dps": statistics.fmean(errors),
        }
    return {
        "height_m": height_m,
        "n_events": len(events),
        "by_arrival_side": by_side,
        "combined_rmse_dps": rmse(all_errors),
        "combined_bias_dps": statistics.fmean(all_errors),
    }


def event_effective_inertias(events: list[Event], height_m: float) -> dict[str, float]:
    values = [
        2.0 * potential_j(event, height_m, complete_circle=False)
        / radians(abs(event.zero_cross_rate_dps)) ** 2
        for event in events
    ]
    return {
        "height_m": height_m,
        "n_events": len(values),
        "mean_kg_m2": statistics.fmean(values),
        "median_kg_m2": statistics.median(values),
        "sample_stdev_kg_m2": statistics.stdev(values),
        "min_kg_m2": min(values),
        "max_kg_m2": max(values),
    }



def height_distribution(fits: dict[str, dict[str, float | int]]) -> dict[str, float | int]:
    values = [float(summary["height_m"]) for summary in fits.values()]
    return {
        "n_runs": len(values),
        "mean_m": statistics.fmean(values),
        "median_m": statistics.median(values),
        "population_stdev_m": statistics.pstdev(values),
        "sample_stdev_m": statistics.stdev(values),
        "min_m": min(values),
        "max_m": max(values),
    }
def write_event_table(path: Path, events: list[Event]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(events[0]))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(event) for event in events)


def write_predictions(path: Path, events: list[Event], fitted_height_m: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(events[0])) + [
        "fixed_j_kg_m2", "pred_h120_dps", "residual_h120_dps",
        "pred_h128_dps", "residual_h128_dps", "pred_h128345_dps",
        "residual_h128345_dps", "pred_fitted_dps", "residual_fitted_dps",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for event in events:
            row = asdict(event)
            inertia = FIXED_V61_DIRECTION_CONDITIONED_J_EFF_FIT_BY_ARRIVAL_SIDE[event.arrival_side]
            row["fixed_j_kg_m2"] = inertia
            for name, height in (
                ("h120", HISTORICAL_MODEL_A_HEIGHT_M),
                ("h128", STANDARD_MODEL_B_HEIGHT_M),
                ("h128345", 0.128345),
                ("fitted", fitted_height_m),
            ):
                prediction = predicted_rate_dps(event, height, inertia)
                row[f"pred_{name}_dps"] = prediction
                row[f"residual_{name}_dps"] = prediction - abs(event.zero_cross_rate_dps)
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append",
                        help="SERIES|RUN|EVENT_CSV|METADATA_JSON; repeat for each run")
    parser.add_argument("--events", type=Path,
                        help="published 54-state CSV; replays the audit without local source files")
    parser.add_argument("--out-events", type=Path, required=True)
    parser.add_argument("--out-provenance", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--comparison-model-b-height-m", type=float, default=0.128345)
    args = parser.parse_args()

    if bool(args.source) == bool(args.events):
        parser.error("provide exactly one of --source or --events")
    if args.events:
        events, source_provenance = read_event_table(args.events), []
    else:
        events, source_provenance = load_sources(args.source)
    if len(events) != 54:
        raise ValueError(f"expected exactly 54 Q-probe pre-command states, got {len(events)}")
    if len({event.run_id for event in events}) != 9:
        raise ValueError("expected exactly nine runs")

    write_event_table(args.out_events, events)
    provenance = {
        "schema_version": 1,
        "analysis_scope": (
            "V55/V56/V58 Q-probe pre-command states. These are not passive "
            "free-decay events and are used only as an external Model-B "
            "parameter-transfer check."
        ),
        "event_csv": {
            "filename": args.out_events.name,
            "sha256": sha256_file(args.out_events),
            "n_events": len(events),
        },
        "extraction_rule": {
            "arrival_side": "requested_side, required equal to observed_side",
            "h_prev_deg": "dynamic_H_prev_deg",
            "zero_cross_rate_dps": "command_rate_bias_corrected_dps",
            "rate_sign_check": "sign(rate) equals arrival_side",
            "selection": "all six Q-probe rows from each of nine specified runs",
        },
        "sources": source_provenance,
    }
    args.out_provenance.parent.mkdir(parents=True, exist_ok=True)
    args.out_provenance.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    fitted_height_m = fit_height_m(events)
    fixed_height_results = {
        "historical_h120": fixed_inertia_summary(events, HISTORICAL_MODEL_A_HEIGHT_M),
        "model_b_h128": fixed_inertia_summary(events, STANDARD_MODEL_B_HEIGHT_M),
        "comparison_h128345": fixed_inertia_summary(events, args.comparison_model_b_height_m),
        "global_optimum": fixed_inertia_summary(events, fitted_height_m),
    }
    series_fits = height_fits(events, "series")
    run_fits = height_fits(events, "run_id")
    flexible_a = flexible_model_summary(events, HISTORICAL_MODEL_A_HEIGHT_M, True)
    flexible_b = flexible_model_summary(events, args.comparison_model_b_height_m, False)
    improvement = 1.0 - flexible_b["combined_rmse_dps"] / flexible_a["combined_rmse_dps"]
    summary = {
        "analysis_name": "v55_v56_v58_qprobe_precommand_model_b_transfer_audit",
        "analysis_scope": provenance["analysis_scope"],
        "n_events": len(events),
        "n_runs": len({event.run_id for event in events}),
        "mass_kg": MASS_KG,
        "fixed_v61_direction_conditioned_J_eff_fit_by_arrival_side_kg_m2": (
            FIXED_V61_DIRECTION_CONDITIONED_J_EFF_FIT_BY_ARRIVAL_SIDE
        ),
        "model_b_parameter_interpretation": (
            "h_eff is a Model-B operational effective height; J_eff_fit is a "
            "direction-conditioned fitted effective inertia. Neither is a direct "
            "physical CG-height or rigid-body inertia measurement."
        ),
        "fixed_height_results": fixed_height_results,
        "height_fit_by_series": series_fits,
        "height_fit_by_run": run_fits,
        "height_fit_by_run_distribution": height_distribution(run_fits),
        "leave_one_run_out_fixed_j": leave_one_run_out(events),
        "eventwise_model_b_implied_J_eff_h_eff128345": event_effective_inertias(
            events, args.comparison_model_b_height_m),
        "flexible_model_comparison": {
            "model_a_complete_circle_h120": flexible_a,
            "model_b_step_h128345": flexible_b,
            "relative_rmse_reduction": improvement,
        },
        "interpretation_limit": (
            "Fitted H is an external dynamic parameter transfer, not a direct "
            "measurement of physical CG height or a lossless free-decay model. "
            "Q-probe/rebuild/contact history can remain in each pre-command state."
        ),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_predictions(args.out_dir / "event_predictions.csv", events, fitted_height_m)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
