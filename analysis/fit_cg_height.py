"""Estimate CG height H from the amplitude dependence of zero-cross speed.

The rigid STEP split-arc geometry is fixed.  For each candidate H, a separate
scale factor is fitted for the two travel directions:

    |omega_zero| ~= beta_side * sqrt(U_B(A; H))

The scale absorbs effective inertia and approximately constant side-specific
loss.  H is therefore identified from the *shape* of the amplitude-speed
relation rather than from an assumed inertia value.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/v61_run2_cg_height_pairs.csv"

R = 0.150
A_INNER = 0.005
MASS = 0.1997
G = 9.80665
C0 = math.sqrt(R * R - A_INNER * A_INNER)
THETA_INNER = math.asin(A_INNER / R)


def delta_h(theta: float, H: float) -> float:
    q = abs(theta)
    if q <= THETA_INNER:
        return H * (math.cos(q) - 1.0) + A_INNER * math.sin(q)
    return R - (C0 - H) * math.cos(q) - H


def potential(theta: float, H: float) -> float:
    return MASS * G * delta_h(theta, H)


def load_rows():
    with DATA.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fit_sensor(rows, rate_key: str, omit: int | None = None):
    use = [r for i, r in enumerate(rows) if i != omit]

    def rmse(H: float) -> float:
        sq = []
        for side in (-1, 1):
            group = [r for r in use if int(r["peak_side"]) == side]
            x = np.array(
                [math.sqrt(potential(math.radians(abs(float(r["peak_angle_video_deg"]))), H)) for r in group]
            )
            y = np.array([abs(float(r[rate_key])) for r in group])
            beta = float(np.dot(x, y) / np.dot(x, x))
            sq.extend((beta * x - y) ** 2)
        return float(math.sqrt(np.mean(sq)))

    opt = minimize_scalar(rmse, bounds=(0.060, 0.145), method="bounded")
    return opt.x, opt.fun


def main():
    rows = load_rows()
    for key, label in (
        ("gyro_rate_at_zero_dps", "gyro"),
        ("video_rate_at_zero_dps", "video local cubic"),
    ):
        H, err = fit_sensor(rows, key)
        loo = [fit_sensor(rows, key, i)[0] for i in range(len(rows))]
        print(
            f"{label}: H={H*1000:.3f} mm, rate RMSE={err:.3f} deg/s, "
            f"LOO H={min(loo)*1000:.3f}..{max(loo)*1000:.3f} mm"
        )


if __name__ == "__main__":
    main()
