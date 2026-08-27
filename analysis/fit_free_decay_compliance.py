"""Fit Model A/B/C to derived V61 run-2 free-decay peak/zero-cross pairs.

No CAD material property is used. Model C stiffness is an effective per-foot
vertical-contact parameter of the reduced screening model.
"""
from __future__ import annotations
import csv
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.compliant_contact import QuasiStaticCompliantContact
from model.foot_compliance import FootArcSection
from model.rocker_geometry import RockerGeometry

MASS_KG = 0.1997
G = 9.80665
DATA_DEFAULT = ROOT / "data/processed/v61_run2_free_decay_peak_zero_pairs.csv"


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        out = []
        for r in csv.DictReader(f):
            out.append(
                (
                    float(r["peak_angle_video_deg"]),
                    abs(float(r["gyro_rate_at_zero_dps"])),
                )
            )
        return out


def golden_minimize(fn, lo, hi, iterations=80):
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


def fit_scale(rows, potential):
    def mse(log_alpha):
        alpha = math.exp(log_alpha)
        err = []
        for angle, rate in rows:
            u = potential(angle)
            if u <= 0.0:
                return float("inf")
            pred = math.sqrt(alpha * u)
            err.append((pred - rate) ** 2)
        return sum(err) / len(err)

    loga, val = golden_minimize(mse, -5.0, 25.0)
    return math.exp(loga), math.sqrt(val)


def fit_by_side(rows, potential):
    sq = []
    detail = {}
    for side in (-1, 1):
        sub = [r for r in rows if (r[0] > 0) == (side > 0)]
        alpha, rmse = fit_scale(sub, potential)
        detail[side] = (alpha, rmse)
        for angle, rate in sub:
            u = potential(angle)
            if u <= 0.0:
                return float("inf"), detail
            sq.append((math.sqrt(alpha * u) - rate) ** 2)
    return math.sqrt(sum(sq) / len(sq)), detail


def logspace(lo, hi, n):
    l0 = math.log(lo)
    l1 = math.log(hi)
    return [math.exp(l0 + (l1 - l0) * i / (n - 1)) for i in range(n)]


def best_c(rows, geom, kmax=1e6, n=400):
    sec = FootArcSection()
    kcrit = sec.symmetric_upright_stability_stiffness_n_per_m(
        MASS_KG, geom.cg_height_upright_m, G
    )
    best = (float("inf"), None, None)
    for k in logspace(kcrit * 1.0001, kmax, n):
        contact = QuasiStaticCompliantContact(geom, k, k)
        rmse, detail = fit_by_side(
            rows,
            lambda a, c=contact: c.screening_total_potential_delta_j(
                math.radians(abs(a)), MASS_KG, G
            ),
        )
        if rmse < best[0]:
            best = (rmse, k, detail)
    return best


def loo(rows, model, geom):
    errs = []
    ks = []
    for i, held in enumerate(rows):
        train = [r for j, r in enumerate(rows) if j != i]
        if model == "A":
            pot = lambda a: geom.complete_circle_potential_delta_j(
                math.radians(abs(a)), MASS_KG, G
            )
        elif model == "B":
            pot = lambda a: geom.potential_delta_j(
                math.radians(abs(a)), MASS_KG, G
            )
        else:
            _, k, _ = best_c(train, geom, n=140)
            ks.append(k)
            c = QuasiStaticCompliantContact(geom, k, k)
            pot = lambda a, c=c: c.screening_total_potential_delta_j(
                math.radians(abs(a)), MASS_KG, G
            )
        side = 1 if held[0] > 0 else -1
        sub = [r for r in train if (r[0] > 0) == (side > 0)]
        alpha, _ = fit_scale(sub, pot)
        pred = math.sqrt(alpha * pot(held[0]))
        errs.append((pred - held[1]) ** 2)
    return math.sqrt(sum(errs) / len(errs)), ks


def main():
    rows = load_rows(DATA_DEFAULT)
    geom = RockerGeometry()
    pot_a = lambda a: geom.complete_circle_potential_delta_j(
        math.radians(abs(a)), MASS_KG, G
    )
    pot_b = lambda a: geom.potential_delta_j(math.radians(abs(a)), MASS_KG, G)
    ra, _ = fit_by_side(rows, pot_a)
    rb, _ = fit_by_side(rows, pot_b)
    rc, kc, _ = best_c(rows, geom)

    print(f"n transitions: {len(rows)}")
    print(f"Model A combined RMSE: {ra:.3f} deg/s")
    print(f"Model B combined RMSE: {rb:.3f} deg/s")
    print(
        f"Model C best RMSE:     {rc:.3f} deg/s at k={kc:.0f} N/m "
        "(search max 1e6)"
    )
    for k in (5000, 10000, 20000, 50000, 100000):
        c = QuasiStaticCompliantContact(geom, k, k)
        r, _ = fit_by_side(
            rows,
            lambda a, c=c: c.screening_total_potential_delta_j(
                math.radians(abs(a)), MASS_KG, G
            ),
        )
        print(f"  C k={k:6d} N/m -> RMSE {r:.3f} deg/s")

    threshold = 1.10 * rb
    lower = None
    for k in logspace(4701.0, 1e6, 1000):
        c = QuasiStaticCompliantContact(geom, k, k)
        r, _ = fit_by_side(
            rows,
            lambda a, c=c: c.screening_total_potential_delta_j(
                math.radians(abs(a)), MASS_KG, G
            ),
        )
        if r <= threshold:
            lower = k
            break
    print(
        "Model-C k needed to stay within +10% of B RMSE: "
        f"~{lower:.0f} N/m"
    )

    for name in ("A", "B", "C"):
        r, ks = loo(rows, name, geom)
        extra = ""
        if ks:
            extra = f", median k={sorted(ks)[len(ks)//2]:.0f} N/m"
        print(f"{name} LOO RMSE: {r:.3f} deg/s{extra}")


if __name__ == "__main__":
    main()
