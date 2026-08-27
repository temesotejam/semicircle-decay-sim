"""Fit left/right effective foot stiffness from a simple force-deflection CSV."""
from __future__ import annotations
import argparse
import csv
from collections import defaultdict
from pathlib import Path


def linear_fit(xs, ys):
    n = len(xs)
    if n < 2:
        raise ValueError("need at least two points")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        raise ValueError("deflection values must vary")
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return slope, intercept, r2


def load(path):
    groups = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("force_N") or not r.get("deflection_mm"):
                continue
            side = r.get("side", "unknown").strip().lower()
            phase = r.get("phase", "loading").strip().lower()
            cycle = r.get("cycle", "").strip()
            force = float(r["force_N"])
            d_m = float(r["deflection_mm"]) * 1e-3
            groups[(side, phase)].append((d_m, force, cycle))
    return groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "csv_path", nargs="?", default="data/foot_stiffness_measurement.csv"
    )
    args = ap.parse_args()
    path = Path(args.csv_path)
    groups = load(path)
    if not groups:
        raise SystemExit("No numeric force_N/deflection_mm rows found.")

    print("side,phase,n,k_N_per_m,intercept_N,R2")
    for (side, phase), rows in sorted(groups.items()):
        xs = [x for x, _, _ in rows]
        ys = [y for _, y, _ in rows]
        k, b, r2 = linear_fit(xs, ys)
        print(f"{side},{phase},{len(rows)},{k:.3f},{b:.6f},{r2:.6f}")

    by = defaultdict(lambda: defaultdict(list))
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("force_N") or not r.get("deflection_mm"):
                continue
            side = r.get("side", "unknown").strip().lower()
            phase = r.get("phase", "loading").strip().lower()
            key = round(float(r["force_N"]), 6)
            by[(side, key)][phase].append(float(r["deflection_mm"]))

    print(
        "\nhysteresis at matched force levels: "
        "side,force_N,unloading_minus_loading_mm"
    )
    for (side, force), ph in sorted(by.items()):
        if ph.get("loading") and ph.get("unloading"):
            dl = sum(ph["loading"]) / len(ph["loading"])
            du = sum(ph["unloading"]) / len(ph["unloading"])
            print(f"{side},{force:.6f},{du-dl:.6f}")


if __name__ == "__main__":
    main()
