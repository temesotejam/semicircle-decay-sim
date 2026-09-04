"""Evaluate STEP-derived angle-dependent foot compliance against historical data.

Two independent passive-data screens are used:
1) V61 run-2 synchronized video peak -> gyro zero-cross rate pairs.
2) 2026-08-28 manual-release median periods at +/-4/8/12/15 deg.

The compliance model does not change Model B in-place.  It is evaluated as a
candidate Model C.  E is an *effective* bending modulus of the load path, not a
claim about bulk filament material.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.rocker_geometry import RockerGeometry
from model.step_cantilever_compliance import StepCantileverCompliance

MASS_KG = 0.1997
G = 9.80665
V61 = ROOT / "data/processed/v61_run2_free_decay_peak_zero_pairs.csv"
PERIODS = ROOT / "data/processed/manual_release_periods_20260828.csv"


def read_v61(path=V61):
    with path.open(newline="", encoding="utf-8") as f:
        return [
            (float(r["peak_angle_video_deg"]), abs(float(r["gyro_rate_at_zero_dps"])))
            for r in csv.DictReader(f)
        ]


def read_periods(path=PERIODS):
    with path.open(newline="", encoding="utf-8") as f:
        return [
            (abs(float(r["anchor_roll_deg"])), float(r["median_period_s"]))
            for r in csv.DictReader(f)
        ]


def fit_rate_scale(rows, potential):
    """Fit rate = beta*sqrt(U) by least squares through the origin."""
    xs = []
    ys = []
    for angle, rate in rows:
        u = potential(angle)
        if u <= 0.0:
            return None, float("inf")
        xs.append(math.sqrt(u))
        ys.append(rate)
    den = sum(x * x for x in xs)
    beta = sum(x * y for x, y in zip(xs, ys)) / den
    rmse = math.sqrt(sum((beta * x - y) ** 2 for x, y in zip(xs, ys)) / len(xs))
    return beta, rmse


def rate_rmse(rows, potential):
    sq = []
    for side in (-1, 1):
        sub = [r for r in rows if (r[0] > 0.0) == (side > 0)]
        beta, _ = fit_rate_scale(sub, potential)
        if beta is None:
            return float("inf")
        for angle, rate in sub:
            sq.append((beta * math.sqrt(potential(angle)) - rate) ** 2)
    return math.sqrt(sum(sq) / len(sq))


def golden_minimize(fn, lo, hi, iterations=70):
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    c = hi - gr * (hi - lo)
    d = lo + gr * (hi - lo)
    fc = fn(c)
    fd = fn(d)
    for _ in range(iterations):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - gr * (hi - lo)
            fc = fn(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + gr * (hi - lo)
            fd = fn(d)
    x = (lo + hi) / 2.0
    return x, fn(x)


def potential_b(geom, angle_deg):
    return geom.potential_delta_j(math.radians(abs(angle_deg)), MASS_KG, G)


def candidate(root_x_m, e_pa):
    return StepCantileverCompliance(
        root_x_m=root_x_m,
        effective_youngs_modulus_pa=e_pa,
    )


def fit_effective_e(rows, root_x_m=0.037):
    def objective(log_e):
        c = candidate(root_x_m, math.exp(log_e))
        return rate_rmse(
            rows,
            lambda a: c.total_potential_delta_j(math.radians(abs(a)), MASS_KG, G),
        )
    loge, rmse = golden_minimize(objective, math.log(4e9), math.log(100e9))
    return math.exp(loge), rmse


def loo_rate(rows, model, root_x_m=0.037):
    err = []
    fitted_e = []
    geom = RockerGeometry()
    for i, held in enumerate(rows):
        train = [r for j, r in enumerate(rows) if j != i]
        if model == "B":
            pot = lambda a: potential_b(geom, a)
        else:
            e_pa, _ = fit_effective_e(train, root_x_m)
            fitted_e.append(e_pa)
            c = candidate(root_x_m, e_pa)
            pot = lambda a, c=c: c.total_potential_delta_j(
                math.radians(abs(a)), MASS_KG, G
            )
        side = 1 if held[0] > 0.0 else -1
        sub = [r for r in train if (r[0] > 0.0) == (side > 0)]
        beta, _ = fit_rate_scale(sub, pot)
        pred = beta * math.sqrt(pot(held[0]))
        err.append(pred - held[1])
    return math.sqrt(sum(x * x for x in err) / len(err)), fitted_e


def period_coefficient(amplitude_deg, potential, n=12000):
    """Conservative full-period coefficient T = coeff*sqrt(J).

    theta=A*(1-y^2) removes the turning-point square-root singularity.  A
    midpoint rule is used so no external numerical package is required.
    """
    A = math.radians(abs(amplitude_deg))
    va = potential(amplitude_deg)
    total = 0.0
    dy = 1.0 / n
    for i in range(n):
        y = (i + 0.5) * dy
        th = A * (1.0 - y * y)
        diff = va - potential(math.degrees(th))
        if diff <= 0.0:
            return float("nan")
        total += (2.0 * A * y) / math.sqrt(2.0 * diff)
    return 4.0 * total * dy


def fit_period_j(rows, potential):
    coeff = [period_coefficient(a, potential) for a, _ in rows]
    if any(not math.isfinite(x) for x in coeff):
        return float("inf"), float("nan")
    obs = [t for _, t in rows]
    den = sum(c * c for c in coeff)
    sqrt_j = sum(c * t for c, t in zip(coeff, obs)) / den
    pred = [c * sqrt_j for c in coeff]
    rmse = math.sqrt(sum((p - t) ** 2 for p, t in zip(pred, obs)) / len(obs))
    return rmse, sqrt_j * sqrt_j


def main():
    geom = RockerGeometry()
    rates = read_v61()
    periods = read_periods()

    pot_b = lambda a: potential_b(geom, a)
    rmse_b = rate_rmse(rates, pot_b)
    loo_b, _ = loo_rate(rates, "B")
    e_best, rmse_c = fit_effective_e(rates)
    loo_c, loo_es = loo_rate(rates, "C")

    print("V61 peak -> zero-cross rate screen")
    print(f"  B rigid STEP RMSE       : {rmse_b:.3f} deg/s")
    print(f"  B LOO RMSE              : {loo_b:.3f} deg/s")
    print(f"  C best effective E      : {e_best/1e9:.3f} GPa")
    print(f"  C best in-sample RMSE   : {rmse_c:.3f} deg/s")
    print(f"  C LOO RMSE              : {loo_c:.3f} deg/s")
    if loo_es:
        s = sorted(loo_es)
        print(f"  C median LOO E          : {s[len(s)//2]/1e9:.3f} GPa")

    print("\nFixed-E sensitivity at STEP root x=37 mm")
    for egpa in (4, 5, 8, 12, 20, 50, 100):
        c = candidate(0.037, egpa * 1e9)
        r = rate_rmse(
            rates,
            lambda a, c=c: c.total_potential_delta_j(
                math.radians(abs(a)), MASS_KG, G
            ),
        )
        print(f"  E={egpa:>3} GPa -> {r:.3f} deg/s")

    print("\nRoot-transition sensitivity")
    for root_mm in (35, 36, 37, 38, 39):
        e_pa, r = fit_effective_e(rates, root_mm / 1000.0)
        loo, _ = loo_rate(rates, "C", root_mm / 1000.0)
        print(
            f"  root={root_mm} mm -> E={e_pa/1e9:.3f} GPa, "
            f"in={r:.3f}, LOO={loo:.3f} deg/s"
        )

    print("\n2026-08-28 passive-period consistency screen")
    rbp, jb = fit_period_j(periods, pot_b)
    print(f"  B rigid: RMSE={rbp:.5f} s, J={jb:.9f} kg m^2")
    for egpa in (8, 12, 20, 50, 100):
        c = candidate(0.037, egpa * 1e9)
        pot = lambda a, c=c: c.total_potential_delta_j(
            math.radians(abs(a)), MASS_KG, G
        )
        r, j = fit_period_j(periods, pot)
        print(f"  C E={egpa:>3} GPa: RMSE={r:.5f} s, J={j:.9f} kg m^2")

    c = candidate(0.037, e_best)
    k0 = c.inner_edge_vertical_stiffness_n_per_m
    half_def = (MASS_KG * G / 2.0) / k0
    full_def = (MASS_KG * G) / k0
    l8 = c.free_arc_length_m(math.radians(8.0))
    i = c.shell_second_moment_m4
    slope8 = (MASS_KG * G) * l8**2 / (2.0 * e_best * i)
    print("\nBest-fit physical-scale interpretation")
    print(f"  inner-edge k ~= {k0/1000:.2f} kN/m per foot")
    print(f"  half-weight tip deflection ~= {half_def*1000:.4f} mm")
    print(f"  full-weight tip deflection ~= {full_def*1000:.4f} mm")
    print(f"  8 deg thin-shell slope ~= {math.degrees(slope8):.4f} deg")


if __name__ == "__main__":
    main()
