"""Generate post-touchdown settling screening values.

Example:
  python analysis/analyze_support_transfer_dynamics.py --csv results/support_transfer.csv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from model.leg_kinematics import LegGeometry
from model.support_transfer import UniformDensitySupportTransferProxy


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path)
    args = ap.parse_args()

    geom = LegGeometry()
    proxy = UniformDensitySupportTransferProxy()
    travels = (5.0, 10.0, 15.0, 20.0)
    pitches = (-5.0, 0.0, 2.5, 5.0, 10.0)
    rows = []
    for alpha in pitches:
        for travel in travels:
            q_touch = geom.q_for_ankle_travel_mm(travel)
            result = proxy.simulate_frictionless_settle(q_touch, alpha)
            p0 = proxy.pose(q_touch, q_touch, alpha)
            pf = proxy.pose(float(result["q_settle_deg"]), q_touch, alpha)
            ty0, tz0 = p0["translation_yz_mm"]
            ty1, tz1 = pf["translation_yz_mm"]
            rows.append({
                "body_pitch_deg": alpha,
                "ankle_travel_mm": travel,
                "q_touch_deg": q_touch,
                "q_settle_deg": result["q_settle_deg"],
                "flat_reachable": result["flat_reachable"],
                "residual_foot_pitch_deg": result["residual_foot_pitch_deg"],
                "energy_drop_mJ": result["energy_drop_mj"],
                "frictionless_proxy_time_ms": result["time_ms"],
                "frictionless_preimpact_qdot_dps": result["preimpact_qdot_dps"],
                "body_delta_y_mm": ty1 - ty0,
                "body_delta_z_mm": tz1 - tz0,
            })

    fields = list(rows[0])
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader(); w.writerows(rows)
    else:
        w = csv.DictWriter(__import__("sys").stdout, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
