"""Evaluate finite-time left/right support transfer against passive data.

Primary data:
- V61 run-2 synchronized video peak -> zero-cross pairs.  Both zero-cross
  rate and peak-to-zero transit time are used.

Independent screen:
- 2026-08-28 manual-release median periods at +/-4/8/12/15 deg.

Model B is the nested rigid limit: transfer_start=0 and tau=0.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.dynamic_support_transfer import DynamicSupportTransfer

MASS_KG = 0.1997
G = 9.80665
V61 = ROOT / "data/processed/v61_run2_free_decay_peak_zero_pairs.csv"
PERIODS = ROOT / "data/processed/manual_release_periods_20260828.csv"

DT_FIT = 0.001
DT_REPORT = 0.00025
J_LO = 4.0e-4
J_HI = 2.0e-3
TRANSFER_GRID_DEG = (0.5, 1.0, 1.5, 1.91, 2.5, 3.0, 4.0)
TAU_GRID_S = (0.002, 0.005, 0.010, 0.020, 0.040, 0.080)


def load_v61(path=V61):
    with path.open(newline="", encoding="utf-8") as f:
        out = []
        for r in csv.DictReader(f):
            out.append(
                {
                    "angle_deg": float(r["peak_angle_video_deg"]),
                    "rate_dps": abs(float(r["gyro_rate_at_zero_dps"])),
                    "transit_s": float(r["zero_cross_time_s"]) - float(r["peak_time_s"]),
                }
            )
        return out


def load_periods(path=PERIODS):
    with path.open(newline="", encoding="utf-8") as f:
        return [
            {
                "angle_deg": float(r["anchor_roll_deg"]),
                "period_s": float(r["median_period_s"]),
            }
            for r in csv.DictReader(f)
        ]


def _rk4_step(model, theta, omega, support, j, dt):
    dynamic = model.transfer_tau_s > 0.0

    def deriv(th, om, s):
        if dynamic:
            ds = model.support_rate(th, s)
            seff = max(-1.0, min(1.0, s))
        else:
            ds = 0.0
            seff = model.instantaneous_support_balance(th)
        torque = model.gravity_torque_nm(th, seff, MASS_KG, G)
        return om, torque / j, ds

    k1 = deriv(theta, omega, support)
    k2 = deriv(
        theta + 0.5 * dt * k1[0],
        omega + 0.5 * dt * k1[1],
        support + 0.5 * dt * k1[2],
    )
    k3 = deriv(
        theta + 0.5 * dt * k2[0],
        omega + 0.5 * dt * k2[1],
        support + 0.5 * dt * k2[2],
    )
    k4 = deriv(
        theta + dt * k3[0],
        omega + dt * k3[1],
        support + dt * k3[2],
    )
    th2 = theta + dt * (k1[0] + 2*k2[0] + 2*k3[0] + k4[0]) / 6.0
    om2 = omega + dt * (k1[1] + 2*k2[1] + 2*k3[1] + k4[1]) / 6.0
    if dynamic:
        s2 = support + dt * (k1[2] + 2*k2[2] + 2*k3[2] + k4[2]) / 6.0
        s2 = max(-1.0, min(1.0, s2))
    else:
        s2 = model.instantaneous_support_balance(th2)
    return th2, om2, s2


def simulate_peak_to_zero(angle_deg, j, model, dt=DT_FIT, max_s=0.8):
    theta = math.radians(angle_deg)
    side = 1.0 if theta > 0.0 else -1.0
    omega = 0.0
    support = side
    t = 0.0
    while t < max_s:
        old_theta, old_omega, old_support, old_t = theta, omega, support, t
        theta, omega, support = _rk4_step(model, theta, omega, support, j, dt)
        t += dt
        if old_theta * theta <= 0.0 and old_theta != theta:
            f = abs(old_theta) / (abs(old_theta) + abs(theta))
            cross_t = old_t + f * dt
            cross_omega = old_omega + f * (omega - old_omega)
            cross_support = old_support + f * (support - old_support)
            return cross_t, abs(math.degrees(cross_omega)), cross_support
        # Failsafe: a candidate that turns away from zero is not admissible.
        if side * theta > side * math.radians(angle_deg) + math.radians(0.5):
            return None
    return None


def row_loss(row, pred):
    if pred is None:
        return 1e6
    t, rate, _ = pred
    er = (rate - row["rate_dps"]) / row["rate_dps"]
    et = (t - row["transit_s"]) / row["transit_s"]
    return er*er + et*et


def golden_log_minimize(fn, lo=J_LO, hi=J_HI, iterations=18):
    a = math.log(lo)
    b = math.log(hi)
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    c = b - gr * (b-a)
    d = a + gr * (b-a)
    fc = fn(math.exp(c))
    fd = fn(math.exp(d))
    for _ in range(iterations):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - gr * (b-a)
            fc = fn(math.exp(c))
        else:
            a, c, fc = c, d, fd
            d = a + gr * (b-a)
            fd = fn(math.exp(d))
    j = math.exp(0.5*(a+b))
    return j, fn(j)


def fit_side_j(rows, model, dt=DT_FIT, iterations=18):
    def objective(j):
        return sum(row_loss(r, simulate_peak_to_zero(r["angle_deg"], j, model, dt)) for r in rows) / len(rows)
    return golden_log_minimize(objective, iterations=iterations)


def fit_js(rows, model, dt=DT_FIT, iterations=18):
    js = {}
    loss = 0.0
    n = 0
    for side in (-1, 1):
        sub = [r for r in rows if (r["angle_deg"] > 0.0) == (side > 0)]
        j, side_loss = fit_side_j(sub, model, dt, iterations)
        js[side] = j
        loss += side_loss * len(sub)
        n += len(sub)
    return js, loss/n


def metrics(rows, model, js, dt=DT_REPORT):
    rate_sq = []
    time_sq = []
    details = []
    for r in rows:
        side = 1 if r["angle_deg"] > 0.0 else -1
        p = simulate_peak_to_zero(r["angle_deg"], js[side], model, dt)
        if p is None:
            return None
        t, rate, support = p
        rate_sq.append((rate-r["rate_dps"])**2)
        time_sq.append((t-r["transit_s"])**2)
        details.append((r["angle_deg"], rate, t, support))
    return {
        "rate_rmse": math.sqrt(sum(rate_sq)/len(rate_sq)),
        "time_rmse": math.sqrt(sum(time_sq)/len(time_sq)),
        "details": details,
    }


def fit_dynamic(rows, dt=DT_FIT, nested=False):
    best = None
    iters = 12 if nested else 18
    for start_deg in TRANSFER_GRID_DEG:
        for tau_s in TAU_GRID_S:
            model = DynamicSupportTransfer(
                transfer_start_rad=math.radians(start_deg),
                transfer_tau_s=tau_s,
            )
            js, loss = fit_js(rows, model, dt, iters)
            cand = (loss, start_deg, tau_s, js)
            if best is None or cand[0] < best[0]:
                best = cand
    return best


def fit_rigid(rows, dt=DT_FIT, nested=False):
    model = DynamicSupportTransfer(transfer_start_rad=0.0, transfer_tau_s=0.0)
    js, loss = fit_js(rows, model, dt, 12 if nested else 18)
    return loss, js


def loo(rows, dynamic):
    rate_err = []
    time_err = []
    selected = []
    for i, held in enumerate(rows):
        train = [r for j, r in enumerate(rows) if j != i]
        if dynamic:
            _, start_deg, tau_s, js = fit_dynamic(train, DT_FIT, nested=True)
            model = DynamicSupportTransfer(
                transfer_start_rad=math.radians(start_deg),
                transfer_tau_s=tau_s,
            )
            selected.append((start_deg, tau_s))
        else:
            _, js = fit_rigid(train, DT_FIT, nested=True)
            model = DynamicSupportTransfer(transfer_start_rad=0.0, transfer_tau_s=0.0)
        side = 1 if held["angle_deg"] > 0.0 else -1
        p = simulate_peak_to_zero(held["angle_deg"], js[side], model, DT_REPORT)
        if p is None:
            rate_err.append(1e3)
            time_err.append(1.0)
        else:
            t, rate, _ = p
            rate_err.append(rate-held["rate_dps"])
            time_err.append(t-held["transit_s"])
    return (
        math.sqrt(sum(e*e for e in rate_err)/len(rate_err)),
        math.sqrt(sum(e*e for e in time_err)/len(time_err)),
        selected,
    )


def simulate_full_period(angle_deg, j, model, dt=0.0005, max_s=2.0):
    theta = math.radians(angle_deg)
    support = 1.0 if theta > 0.0 else -1.0
    omega = 0.0
    t = 0.0
    extrema = 0
    # first step establishes inward motion and avoids counting t=0 as a peak
    theta, omega, support = _rk4_step(model, theta, omega, support, j, dt)
    t += dt
    prev_omega = omega
    while t < max_s:
        old_omega = omega
        theta, omega, support = _rk4_step(model, theta, omega, support, j, dt)
        t += dt
        if old_omega * omega < 0.0:
            extrema += 1
            if extrema == 2:
                return t
        prev_omega = omega
        if abs(theta) > math.radians(30.0):
            return None
    return None


def period_rmse(rows, model, j, dt=0.001):
    sq = []
    for r in rows:
        p = simulate_full_period(r["angle_deg"], j, model, dt)
        if p is None:
            return 1e3
        sq.append((p-r["period_s"])**2)
    return math.sqrt(sum(sq)/len(sq))


def fit_period_j(rows, model, iterations=16):
    return golden_log_minimize(lambda j: period_rmse(rows, model, j), iterations=iterations)


def fit_period_dynamic(rows):
    best = None
    for start_deg in TRANSFER_GRID_DEG:
        for tau_s in TAU_GRID_S:
            model = DynamicSupportTransfer(transfer_start_rad=math.radians(start_deg), transfer_tau_s=tau_s)
            j, rmse = fit_period_j(rows, model, iterations=12)
            cand = (rmse, start_deg, tau_s, j)
            if best is None or cand[0] < best[0]:
                best = cand
    return best


def main():
    rows = load_v61()
    periods = load_periods()

    rigid_loss, rigid_js = fit_rigid(rows)
    rigid_model = DynamicSupportTransfer(transfer_start_rad=0.0, transfer_tau_s=0.0)
    rigid_m = metrics(rows, rigid_model, rigid_js)

    dyn_loss, start_deg, tau_s, dyn_js = fit_dynamic(rows)
    dyn_model = DynamicSupportTransfer(transfer_start_rad=math.radians(start_deg), transfer_tau_s=tau_s)
    dyn_m = metrics(rows, dyn_model, dyn_js)

    print("V61 peak -> zero-cross joint rate/time fit")
    print(f"  B objective            : {rigid_loss:.6f}")
    print(f"  B J- / J+              : {rigid_js[-1]:.9f} / {rigid_js[1]:.9f} kg m^2")
    print(f"  B rate RMSE            : {rigid_m['rate_rmse']:.3f} deg/s")
    print(f"  B transit-time RMSE    : {rigid_m['time_rmse']*1000:.2f} ms")
    print(f"  D objective            : {dyn_loss:.6f}")
    print(f"  D transfer start       : {start_deg:.3f} deg")
    print(f"  D transfer tau         : {tau_s*1000:.1f} ms")
    print(f"  D J- / J+              : {dyn_js[-1]:.9f} / {dyn_js[1]:.9f} kg m^2")
    print(f"  D rate RMSE            : {dyn_m['rate_rmse']:.3f} deg/s")
    print(f"  D transit-time RMSE    : {dyn_m['time_rmse']*1000:.2f} ms")

    br, bt, _ = loo(rows, False)
    dr, dtm, selected = loo(rows, True)
    print("\nNested leave-one-out")
    print(f"  B rate RMSE            : {br:.3f} deg/s")
    print(f"  B transit-time RMSE    : {bt*1000:.2f} ms")
    print(f"  D rate RMSE            : {dr:.3f} deg/s")
    print(f"  D transit-time RMSE    : {dtm*1000:.2f} ms")
    if selected:
        starts = sorted(x[0] for x in selected)
        taus = sorted(x[1] for x in selected)
        print(f"  D median selected start: {starts[len(starts)//2]:.3f} deg")
        print(f"  D median selected tau  : {taus[len(taus)//2]*1000:.1f} ms")

    print("\nIndependent 2026-08-28 period screen")
    jb, rb = fit_period_j(periods, rigid_model)
    jd, rd = fit_period_j(periods, dyn_model)
    print(f"  B best period J        : {jb:.9f} kg m^2")
    print(f"  B period RMSE          : {rb*1000:.2f} ms")
    print(f"  D(V61 params) J        : {jd:.9f} kg m^2")
    print(f"  D(V61 params) RMSE     : {rd*1000:.2f} ms")
    rp, sp, tp, jp = fit_period_dynamic(periods)
    print(f"  D period-only best     : start={sp:.3f} deg, tau={tp*1000:.1f} ms")
    print(f"  D period-only J        : {jp:.9f} kg m^2")
    print(f"  D period-only RMSE     : {rp*1000:.2f} ms")

    print("\nV61 event detail for selected D")
    print("  angle_deg, obs_rate, pred_rate, obs_ms, pred_ms, support_at_zero")
    for r, det in zip(rows, dyn_m["details"]):
        _, rate, t, support = det
        print(
            f"  {r['angle_deg']:+.3f}, {r['rate_dps']:.3f}, {rate:.3f}, "
            f"{r['transit_s']*1000:.2f}, {t*1000:.2f}, {support:+.3f}"
        )


if __name__ == "__main__":
    main()
