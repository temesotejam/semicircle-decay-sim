from __future__ import annotations

import csv
from pathlib import Path

from analysis.audit_crossrun_qprobe_prestate import (
    Event,
    FIXED_V61_J_BY_ARRIVAL_SIDE,
    fixed_inertia_summary,
    fit_height_m,
    flexible_model_summary,
)


ROOT = Path(__file__).resolve().parents[1]


def published_events() -> list[Event]:
    path = ROOT / "data" / "v55_v56_v58_qprobe_precommand_events.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [
        Event(
            series=row["series"], run_id=row["run_id"],
            source_probe_index=int(row["source_probe_index"]),
            q_probe_schedule_id=int(row["q_probe_schedule_id"]),
            planned_probe_index=int(row["planned_probe_index"]),
            q_target_mA_s=float(row["q_target_mA_s"]),
            q_effective_mA_s=float(row["q_effective_mA_s"]),
            arrival_side=int(row["arrival_side"]),
            h_prev_deg=float(row["h_prev_deg"]),
            zero_cross_rate_dps=float(row["zero_cross_rate_dps"]),
        )
        for row in rows
    ]


def test_published_crossrun_height_audit_regression() -> None:
    events = published_events()
    assert len(events) == 54
    assert {event.arrival_side for event in events} == {-1, +1}
    assert {event.run_id for event in events} == {
        "V55_run1", "V55_run2", "V55_run3",
        "V56_run1", "V56_run2", "V56_run3",
        "V58_run1", "V58_run2", "V58_run3",
    }
    assert FIXED_V61_J_BY_ARRIVAL_SIDE == {-1: 0.928e-3, +1: 0.795e-3}

    optimum = fit_height_m(events)
    assert abs(optimum - 0.1269323693) < 1e-8
    assert abs(fixed_inertia_summary(events, 0.120)["rmse_dps"] - 7.3730686603) < 1e-8
    assert abs(fixed_inertia_summary(events, 0.128)["rmse_dps"] - 3.5866768670) < 1e-8

    model_a = flexible_model_summary(events, 0.120, True)
    model_b = flexible_model_summary(events, 0.128345, False)
    assert abs(model_a["combined_rmse_dps"] - 4.1614423034) < 1e-8
    assert abs(model_b["combined_rmse_dps"] - 2.6201675372) < 1e-8
