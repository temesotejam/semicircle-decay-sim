"""Compare A complete-circle, B rigid split-arc, and C compliant screening."""
from __future__ import annotations
import argparse
import csv
from math import radians
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.compliant_contact import QuasiStaticCompliantContact
from model.rocker_geometry import RockerGeometry


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--mass-kg", type=float, default=0.1997)
    p.add_argument("--max-deg", type=float, default=17.0)
    p.add_argument("--step-deg", type=float, default=0.05)
    p.add_argument(
        "--stiffness",
        type=float,
        nargs="*",
        default=[5000.0, 7500.0, 10000.0, 15000.0],
        help="per-foot effective vertical stiffness values [N/m] for Model C",
    )
    p.add_argument("--output", default="results/model_abc_potential_sweep.csv")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    geom = RockerGeometry()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    contacts = {k: QuasiStaticCompliantContact(geom, k, k) for k in args.stiffness}
    fields = ["angle_deg", "A_complete_circle_mJ", "B_rigid_split_arc_mJ"]
    fields += [f"C_compliant_k_{int(k)}_mJ" for k in args.stiffness]
    fields += [f"C_mode_k_{int(k)}" for k in args.stiffness]

    rows = []
    n = int(round(args.max_deg / args.step_deg))
    for i in range(n + 1):
        deg = i * args.step_deg
        th = radians(deg)
        row = {
            "angle_deg": deg,
            "A_complete_circle_mJ": geom.complete_circle_potential_delta_j(
                th, args.mass_kg
            ) * 1e3,
            "B_rigid_split_arc_mJ": geom.potential_delta_j(
                th, args.mass_kg
            ) * 1e3,
        }
        for k, contact in contacts.items():
            row[f"C_compliant_k_{int(k)}_mJ"] = (
                contact.screening_total_potential_delta_j(th, args.mass_kg) * 1e3
            )
            row[f"C_mode_k_{int(k)}"] = contact.solve(
                th, args.mass_kg * 9.80665
            ).mode
        rows.append(row)

    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(out)


if __name__ == "__main__":
    main()
