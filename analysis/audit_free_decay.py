"""Reproducibility audit for passive free-decay models.

Input is an event-level CSV extracted from synchronized RWLOG/video runs.
The script deliberately keeps three passive descriptions separate:

Model A
    Historical complete-circle potential geometry.
Model B
    STEP-derived piecewise rigid rocker geometry.
Empirical map
    Half-cycle amplitude map A_next = r*A_prev + c (or proportional r*A_prev),
    selected with a support-aware LOOCV rule similar to the firmware calibration.

Models A/B are compared on peak -> zero-cross speed. The empirical map is
compared on peak -> next-peak amplitude. They share the same event table, but
their RMSE values must not be mixed because the target quantities differ.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from math import degrees, radians, sqrt
from pathlib import Path
from typing import Callable, Iterable

from model.rocker_geometry import RockerGeometry


@dataclass(frozen=True)
class Event:
    run_id: str
    event_id: str
    prev_peak_side: int
    prev_peak_deg: float
    zero_cross_rate_dps: float
    next_peak_deg: float | None


@dataclass(frozen=True)
class LinearMap:
    kind: str
    r: float
    c: float
    support_min_deg: float
    support_max_deg: float
    loocv_rmse_deg: float | None
    valid_halfcycle: bool

    def predict(self, x_deg: float) -> float:
        return self.r * x_deg + self.c


def rmse(values: Iterable[float]) -> float | None:
    vals = list(values)
    if not vals:
        return None
    return sqrt(sum(v * v for v in vals) / len(vals))


def parse_side(raw: str, prev_peak_deg: float) -> int:
    s = (raw or "").strip().lower()
    if s in {"-1", "-", "neg", "negative", "left"}:
        return -1
    if s in {"+1", "1", "+", "pos", "positive", "right"}:
        return +1
    if prev_peak_deg < 0:
        return -1
    if prev_peak_deg > 0:
        return +1
    raise ValueError("prev_peak_side is missing/invalid and prev_peak_deg is zero")


def read_events(path: Path) -> list[Event]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    required = {"prev_peak_deg", "zero_cross_rate_dps"}
    missing = required - set(rows[0].keys() if rows else [])
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    events: list[Event] = []
    for i, row in enumerate(rows, start=1):
        prev = float(row["prev_peak_deg"])
        side = parse_side(row.get("prev_peak_side", ""), prev)
        next_raw = (row.get("next_peak_deg") or "").strip()
        events.append(
            Event(
                run_id=(row.get("run_id") or path.stem).strip(),
                event_id=(row.get("event_id") or str(i)).strip(),
                prev_peak_side=side,
                prev_peak_deg=prev,
                zero_cross_rate_dps=float(row["zero_cross_rate_dps"]),
                next_peak_deg=float(next_raw) if next_raw else None,
            )
        )
    return events


def fit_effective_inertia(
    events: list[Event],
    potential_fn: Callable[[float], float],
) -> float:
    if not events:
        raise ValueError("cannot fit inertia with zero events")

    # omega_rad_s = sqrt(2U/J) = k*sqrt(2U), with k=1/sqrt(J).
    xs = [sqrt(max(0.0, 2.0 * potential_fn(abs(e.prev_peak_deg)))) for e in events]
    ys = [radians(abs(e.zero_cross_rate_dps)) for e in events]
    denom = sum(x * x for x in xs)
    if denom <= 0.0:
        raise ValueError("degenerate potential values")
    k = sum(x * y for x, y in zip(xs, ys)) / denom
    if k <= 0.0:
        raise ValueError("non-positive fitted speed scale")
    return 1.0 / (k * k)


def predict_cross_rate_dps(
    event: Event,
    j_kg_m2: float,
    potential_fn: Callable[[float], float],
) -> float:
    u = max(0.0, potential_fn(abs(event.prev_peak_deg)))
    return degrees(sqrt(2.0 * u / j_kg_m2))


def loocv_cross_rmse(
    events: list[Event],
    potential_fn: Callable[[float], float],
) -> float | None:
    if len(events) < 3:
        return None
    errors: list[float] = []
    for i, held in enumerate(events):
        train = events[:i] + events[i + 1 :]
        j = fit_effective_inertia(train, potential_fn)
        pred = predict_cross_rate_dps(held, j, potential_fn)
        errors.append(pred - abs(held.zero_cross_rate_dps))
    return rmse(errors)


def fit_linear_map_no_loocv(events: list[Event], kind: str) -> LinearMap:
    pairs = [
        (abs(e.prev_peak_deg), abs(e.next_peak_deg))
        for e in events
        if e.next_peak_deg is not None
    ]
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    if len(pairs) < 2:
        raise ValueError("at least two pairs are required")

    if kind == "proportional":
        denom = sum(x * x for x in xs)
        if denom <= 0.0:
            raise ValueError("degenerate amplitude inputs")
        r = sum(x * y for x, y in pairs) / denom
        c = 0.0
    elif kind == "affine":
        xm = sum(xs) / len(xs)
        ym = sum(ys) / len(ys)
        denom = sum((x - xm) ** 2 for x in xs)
        if denom <= 0.0:
            raise ValueError("degenerate amplitude inputs")
        r = sum((x - xm) * (y - ym) for x, y in pairs) / denom
        c = ym - r * xm
    else:
        raise ValueError(f"unknown map kind: {kind}")

    lo, hi = min(xs), max(xs)
    return LinearMap(
        kind=kind,
        r=r,
        c=c,
        support_min_deg=lo,
        support_max_deg=hi,
        loocv_rmse_deg=None,
        valid_halfcycle=(
            r > 0.0 and r * lo + c > 0.0 and r * hi + c > 0.0
        ),
    )


def fit_linear_map(events: list[Event], kind: str) -> LinearMap:
    fitted = fit_linear_map_no_loocv(events, kind)
    pairs = [e for e in events if e.next_peak_deg is not None]

    loo_errors: list[float] = []
    if len(pairs) >= 3:
        for i, held in enumerate(pairs):
            train = pairs[:i] + pairs[i + 1 :]
            try:
                m = fit_linear_map_no_loocv(train, kind)
            except ValueError:
                continue
            loo_errors.append(
                m.predict(abs(held.prev_peak_deg)) - abs(held.next_peak_deg)
            )

    return LinearMap(
        kind=fitted.kind,
        r=fitted.r,
        c=fitted.c,
        support_min_deg=fitted.support_min_deg,
        support_max_deg=fitted.support_max_deg,
        loocv_rmse_deg=rmse(loo_errors),
        valid_halfcycle=fitted.valid_halfcycle,
    )


def composition_domain(start: LinearMap, other: LinearMap) -> tuple[float, float] | None:
    if start.r <= 0.0:
        return None
    lo = max(
        start.support_min_deg,
        (other.support_min_deg - start.c) / start.r,
    )
    hi = min(
        start.support_max_deg,
        (other.support_max_deg - start.c) / start.r,
    )
    if hi < lo:
        return None
    return lo, hi


def full_cycle_valid(start: LinearMap, other: LinearMap) -> bool:
    domain = composition_domain(start, other)
    if domain is None:
        return False
    lo, hi = domain

    def f(x: float) -> float:
        return other.predict(start.predict(x))

    # F(x) and x-F(x) are linear, so endpoint checks are sufficient.
    for x in (lo, hi):
        y = f(x)
        if not (y > 0.0 and y < x):
            return False
    return True


def linear_map_to_dict(m: LinearMap) -> dict[str, object]:
    return {
        "kind": m.kind,
        "r": m.r,
        "c_deg": m.c,
        "support_min_deg": m.support_min_deg,
        "support_max_deg": m.support_max_deg,
        "loocv_rmse_deg": m.loocv_rmse_deg,
        "valid_halfcycle": m.valid_halfcycle,
    }


def select_empirical_maps(
    by_side: dict[int, list[Event]],
) -> tuple[dict[int, LinearMap], dict[str, object]]:
    candidates: dict[int, list[LinearMap]] = {}
    for side in (-1, +1):
        pairs = [e for e in by_side.get(side, []) if e.next_peak_deg is not None]
        if len(pairs) < 2:
            candidates[side] = []
            continue
        candidates[side] = [
            fit_linear_map(pairs, "proportional"),
            fit_linear_map(pairs, "affine"),
        ]

    combos: list[tuple[float, LinearMap, LinearMap]] = []
    for neg in candidates[-1]:
        for pos in candidates[+1]:
            if not (neg.valid_halfcycle and pos.valid_halfcycle):
                continue
            if not (full_cycle_valid(neg, pos) and full_cycle_valid(pos, neg)):
                continue
            scores = [
                s
                for s in (neg.loocv_rmse_deg, pos.loocv_rmse_deg)
                if s is not None
            ]
            score = sum(scores) / len(scores) if scores else float("inf")
            combos.append((score, neg, pos))

    selected: dict[int, LinearMap] = {}
    if combos:
        combos.sort(key=lambda item: item[0])
        _, neg, pos = combos[0]
        selected = {-1: neg, +1: pos}

    diag = {
        "candidates": {
            str(side): [linear_map_to_dict(m) for m in maps]
            for side, maps in candidates.items()
        },
        "selected": {
            str(side): linear_map_to_dict(m) for side, m in selected.items()
        },
        "selection_rule": (
            "positive monotone proportional/affine half-cycle candidates; "
            "both composed full cycles must satisfy 0<F(A)<A over their "
            "composition domains; choose lowest mean LOOCV RMSE; no extrapolation"
        ),
    }
    return selected, diag


def model_summary(
    by_side: dict[int, list[Event]],
    potential_fn: Callable[[float], float],
) -> dict[str, object]:
    out: dict[str, object] = {}
    all_errors: list[float] = []
    all_loo_errors: list[float] = []
    for side in (-1, +1):
        events = by_side.get(side, [])
        if not events:
            continue
        j = fit_effective_inertia(events, potential_fn)
        errs = [
            predict_cross_rate_dps(e, j, potential_fn)
            - abs(e.zero_cross_rate_dps)
            for e in events
        ]
        out[str(side)] = {
            "n": len(events),
            "J_eff_kg_m2": j,
            "rmse_dps": rmse(errs),
            "loocv_rmse_dps": loocv_cross_rmse(events, potential_fn),
        }
        all_errors.extend(errs)

        if len(events) >= 3:
            for i, held in enumerate(events):
                train = events[:i] + events[i + 1 :]
                j_loo = fit_effective_inertia(train, potential_fn)
                all_loo_errors.append(
                    predict_cross_rate_dps(held, j_loo, potential_fn)
                    - abs(held.zero_cross_rate_dps)
                )

    out["combined_rmse_dps"] = rmse(all_errors)
    out["combined_loocv_rmse_dps"] = rmse(all_loo_errors)
    return out


def write_event_predictions(
    path: Path,
    events: list[Event],
    geom: RockerGeometry,
    mass_kg: float,
    selected_maps: dict[int, LinearMap],
    model_a: dict[str, object],
    model_b: dict[str, object],
) -> None:
    fields = [
        "run_id",
        "event_id",
        "prev_peak_side",
        "prev_peak_deg",
        "zero_cross_rate_dps",
        "next_peak_deg",
        "contact_mode_geom",
        "model_a_cross_pred_dps",
        "model_a_cross_residual_dps",
        "model_b_cross_pred_dps",
        "model_b_cross_residual_dps",
        "empirical_next_peak_pred_deg",
        "empirical_next_peak_residual_deg",
        "empirical_in_support",
    ]

    def ua(angle_deg: float) -> float:
        return geom.complete_circle_potential_delta_j(radians(angle_deg), mass_kg)

    def ub(angle_deg: float) -> float:
        return geom.potential_delta_j(radians(angle_deg), mass_kg)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for e in events:
            side_key = str(e.prev_peak_side)
            ja = model_a[side_key]["J_eff_kg_m2"]
            jb = model_b[side_key]["J_eff_kg_m2"]
            pa = predict_cross_rate_dps(e, ja, ua)
            pb = predict_cross_rate_dps(e, jb, ub)

            emap = selected_maps.get(e.prev_peak_side)
            empirical_pred: float | str = ""
            empirical_resid: float | str = ""
            empirical_support: int | str = ""
            if emap is not None and e.next_peak_deg is not None:
                x = abs(e.prev_peak_deg)
                in_support = emap.support_min_deg <= x <= emap.support_max_deg
                empirical_support = int(in_support)
                if in_support:
                    pred = emap.predict(x)
                    empirical_pred = pred
                    empirical_resid = pred - abs(e.next_peak_deg)

            w.writerow(
                {
                    "run_id": e.run_id,
                    "event_id": e.event_id,
                    "prev_peak_side": e.prev_peak_side,
                    "prev_peak_deg": e.prev_peak_deg,
                    "zero_cross_rate_dps": e.zero_cross_rate_dps,
                    "next_peak_deg": "" if e.next_peak_deg is None else e.next_peak_deg,
                    "contact_mode_geom": geom.contact_mode(radians(e.prev_peak_deg)),
                    "model_a_cross_pred_dps": pa,
                    "model_a_cross_residual_dps": pa - abs(e.zero_cross_rate_dps),
                    "model_b_cross_pred_dps": pb,
                    "model_b_cross_residual_dps": pb - abs(e.zero_cross_rate_dps),
                    "empirical_next_peak_pred_deg": empirical_pred,
                    "empirical_next_peak_residual_deg": empirical_resid,
                    "empirical_in_support": empirical_support,
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("events_csv", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--mass-kg", type=float, default=0.1997)
    args = parser.parse_args()

    events = read_events(args.events_csv)
    if not events:
        raise SystemExit("no events")

    geom = RockerGeometry()
    by_side = {
        side: [e for e in events if e.prev_peak_side == side]
        for side in (-1, +1)
    }

    def ua(angle_deg: float) -> float:
        return geom.complete_circle_potential_delta_j(radians(angle_deg), args.mass_kg)

    def ub(angle_deg: float) -> float:
        return geom.potential_delta_j(radians(angle_deg), args.mass_kg)

    model_a = model_summary(by_side, ua)
    model_b = model_summary(by_side, ub)
    selected_maps, map_diag = select_empirical_maps(by_side)

    summary = {
        "input_csv": str(args.events_csv),
        "n_events": len(events),
        "mass_kg": args.mass_kg,
        "geometry": {
            "radius_m": geom.radius_m,
            "inner_edge_x_m": geom.inner_edge_x_m,
            "outer_edge_x_m": geom.outer_edge_x_m,
            "cg_height_upright_m": geom.cg_height_upright_m,
            "theta_inner_deg": degrees(geom.theta_inner_rad),
            "theta_outer_deg": degrees(geom.theta_outer_rad),
        },
        "model_a_complete_circle_cross_rate": model_a,
        "model_b_step_geometry_cross_rate": model_b,
        "empirical_halfcycle_map": map_diag,
        "metric_warning": (
            "Model A/B RMSE target zero-cross rate [deg/s]; empirical-map RMSE "
            "target next-peak amplitude [deg]. Do not rank these numeric RMSEs directly."
        ),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_event_predictions(
        args.out_dir / "event_predictions.csv",
        events,
        geom,
        args.mass_kg,
        selected_maps,
        model_a,
        model_b,
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
