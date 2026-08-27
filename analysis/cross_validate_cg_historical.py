"""Cross-validate Model-B CG height against older V55/V56/V58 states.

The historical rows are pre-pulse Q-probe states extracted from study_AT.
They are NOT clean passive identification data; they are used only as an
external-transfer/generalization test.

Strict transfer test:
- keep STEP geometry fixed,
- keep the V61-derived direction-wise effective J fixed,
- vary only H and predict zero-cross speed from predecessor amplitude.
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/historical_qprobe_state_cross_validation.csv"

R = 0.150
A = 0.005
M = 0.1997
G = 9.80665
C0 = math.sqrt(R * R - A * A)
THETA_INNER = math.asin(A / R)

# From V61 run-2 passive Model-B fit at H=128.345 mm.
# side is travel/command-rate sign in the historical pre-pulse table.
J_V61 = {-1: 0.928e-3, +1: 0.795e-3}


def load_rows():
    with DATA.open(newline="", encoding="utf-8") as f:
        rows = []
        for r in csv.DictReader(f):
            rows.append({
                "version": r["version"],
                "run": r["run"],
                "side": int(r["side"]),
                "A": float(r["Hprev_dynamic_deg"]),
                "rate": float(r["abs_rate_dps"]),
                "A_video": float(r["Hprev_video_deg"]),
            })
        return rows


def dh_b(angle_deg: float, H: float) -> float:
    q = abs(math.radians(angle_deg))
    if q <= THETA_INNER:
        return H * (math.cos(q) - 1.0) + A * math.sin(q)
    return R - (C0 - H) * math.cos(q) - H


def dh_a(angle_deg: float, H: float) -> float:
    q = abs(math.radians(angle_deg))
    return (R - H) * (1.0 - math.cos(q))


def speed_from_j(angle_deg: float, H: float, J: float, model: str = "B") -> float:
    dh = dh_b(angle_deg, H) if model == "B" else dh_a(angle_deg, H)
    w = math.sqrt(max(0.0, 2.0 * M * G * dh / J))
    return math.degrees(w)


def rmse_bias_fixed_j(rows, H: float):
    e = [speed_from_j(r["A"], H, J_V61[r["side"]]) - r["rate"] for r in rows]
    return math.sqrt(mean(x * x for x in e)), mean(e)


def scan_h(rows, lo=0.115, hi=0.140, n=10001):
    best = None
    for i in range(n):
        H = lo + (hi - lo) * i / (n - 1)
        rmse, bias = rmse_bias_fixed_j(rows, H)
        if best is None or rmse < best[0]:
            best = (rmse, H, bias)
    return best


def fit_j_by_side(rows, H: float, model: str):
    sq = []
    out = {}
    for side in (-1, +1):
        group = [r for r in rows if r["side"] == side]
        x = []
        y = []
        for r in group:
            dh = dh_b(r["A"], H) if model == "B" else dh_a(r["A"], H)
            x.append(math.sqrt(M * G * dh))
            y.append(r["rate"])
        beta = sum(a*b for a, b in zip(x, y)) / sum(a*a for a in x)
        J = 2.0 * (180.0 / math.pi) ** 2 / beta**2
        out[side] = J
        sq.extend((beta*a - b) ** 2 for a, b in zip(x, y))
    return math.sqrt(mean(sq)), out


def implied_j(row, H: float):
    U = M * G * dh_b(row["A"], H)
    w = math.radians(row["rate"])
    return 2.0 * U / (w*w)


def group_rows(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[r[key]].append(r)
    return out


def main():
    rows = load_rows()
    print(f"historical states: {len(rows)}")

    for H in (0.120, 0.128345):
        r, b = rmse_bias_fixed_j(rows, H)
        print(f"strict transfer H={H*1000:.3f} mm: RMSE={r:.3f}, bias={b:+.3f} deg/s")

    best_rmse, best_h, best_bias = scan_h(rows)
    print(f"strict-transfer best H={best_h*1000:.3f} mm: RMSE={best_rmse:.3f}, bias={best_bias:+.3f}")

    print("\nVersion pooled best H with V61 J frozen:")
    for name, group in sorted(group_rows(rows, "version").items()):
        r, h, b = scan_h(group)
        print(f"  {name}: H={h*1000:.3f} mm, RMSE={r:.3f}, bias={b:+.3f}")

    run_h = []
    print("\nPer-run best H with V61 J frozen:")
    for name, group in sorted(group_rows(rows, "run").items()):
        r, h, b = scan_h(group)
        run_h.append(h * 1000.0)
        print(f"  {name}: H={h*1000:.3f} mm, RMSE={r:.3f}")
    print(
        f"  run-H mean={mean(run_h):.3f}, median={median(run_h):.3f}, "
        f"sd={pstdev(run_h):.3f}, range={min(run_h):.3f}..{max(run_h):.3f} mm"
    )

    print("\nShape comparison with direction-wise J refitted on these 54 states:")
    ra, ja = fit_j_by_side(rows, 0.120, "A")
    rb, jb = fit_j_by_side(rows, 0.128345, "B")
    print(f"  Model A H=120: RMSE={ra:.3f}, J-={ja[-1]*1e3:.4f}e-3, J+={ja[1]*1e3:.4f}e-3")
    print(f"  Model B H=128.345: RMSE={rb:.3f}, J-={jb[-1]*1e3:.4f}e-3, J+={jb[1]*1e3:.4f}e-3")
    print(f"  RMSE reduction={(ra-rb)/ra*100:.1f}%")

    js = [implied_j(r, 0.128345) for r in rows]
    print("\nImplied Model-B energy-fit J at H=128.345 mm:")
    print(
        f"  mean={mean(js)*1e3:.4f}e-3, median={median(js)*1e3:.4f}e-3, "
        f"sd={pstdev(js)*1e3:.4f}e-3 kg m^2"
    )


if __name__ == "__main__":
    main()
