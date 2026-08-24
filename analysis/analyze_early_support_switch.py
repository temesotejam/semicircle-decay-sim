"""Generate the geometry/proxy-dynamics map for early support switching.

The committed default answers two separate questions without mixing them:

1. Geometry: if the swing leg is captured at q before the q=-20 deg hard stop,
   how much of the maximum ankle-center travel has been used?
2. Ideal passive time scale: under the equal-density STEP proxy and zero body
   pitch/friction, when is that q reached after release from q=0?

The timing columns are screening values only.  The geometric travel columns are
fixed by the audited joint/STEP dimensions.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.leg_kinematics import LegGeometry
from model.passive_swing import interpolate_state_at_q, simulate_until_stop, uniform_step_proxy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--body-pitch", type=float, default=0.0)
    args = ap.parse_args()

    geom = LegGeometry()
    proxy = uniform_step_proxy()
    trajectory, impact = simulate_until_stop(
        proxy,
        body_pitch_deg=args.body_pitch,
        dt_s=1e-5,
    )
    if impact is None:
        raise RuntimeError("The proxy swing did not reach q_min")

    q_values = (0.0, -2.5, -5.0, -7.5, -10.0, -12.5, -15.0, -17.5, -20.0)
    rows = []
    for q in q_values:
        t_s, qdot_dps = interpolate_state_at_q(trajectory, q)
        ankle_y, ankle_z = geom.ankle_position_mm(q)
        travel = geom.ankle_travel_from_qmax_mm(q)
        rows.append(
            {
                "q_switch_deg": q,
                "ankle_y_mm": ankle_y,
                "ankle_z_mm": ankle_z,
                "ankle_travel_from_q0_mm": travel,
                "max_stride_fraction": geom.stride_fraction_from_qmax(q),
                "ideal_uniform_step_proxy_time_ms": 1000.0 * t_s,
                "ideal_uniform_step_proxy_qdot_dps": qdot_dps,
            }
        )

    fields = list(rows[0])
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
