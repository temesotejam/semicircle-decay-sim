"""Map swing-leg angle to the body-roll angle at first possible touchdown.

This is a STEP-geometry kinematic audit, not yet a force/contact simulation.
For a chosen stance-leg angle and swing-leg angle, both feet are transformed by
one common body roll.  The common vertical translation that would put the
stance foot on an infinite horizontal floor cancels, so touchdown occurs when

    zmin(swing foot) - zmin(stance foot) = 0.

This directly tests the proposed control idea: changing body roll with the
reaction wheel can transfer support before the swing leg reaches its q=-20 deg
hard stop, thereby selecting a shorter geometric step.

Default convention:
- right leg = stance/support candidate
- left leg = swing candidate
- positive roll about STEP +Y lowers the right side and raises the left side
- body fore-aft pitch is 0 deg in the committed reference map

Usage:
    python analysis/audit_early_touchdown_roll_map.py \
        "Part Studio 1.1.step" --csv touchdown_roll_map.csv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cadquery as cq

from model.leg_kinematics import LegGeometry

LEFT_FOOT_ID = 7
RIGHT_FOOT_ID = 9
HIP_Y_MM = 0.0
HIP_Z_MM = -12.0


def rotate_about_x(shape, angle_deg: float, y_mm: float, z_mm: float):
    return shape.rotate(
        cq.Vector(-1000.0, y_mm, z_mm),
        cq.Vector(+1000.0, y_mm, z_mm),
        angle_deg,
    )


def rotate_about_y(shape, angle_deg: float):
    return shape.rotate(
        cq.Vector(0.0, -1000.0, 0.0),
        cq.Vector(0.0, +1000.0, 0.0),
        angle_deg,
    )


def transform_foot(foot, q_deg: float, body_pitch_deg: float, roll_deg: float):
    # Relative hip rotation first, then common body pitch, then common body roll.
    out = rotate_about_x(foot, q_deg, HIP_Y_MM, HIP_Z_MM)
    out = rotate_about_x(out, body_pitch_deg, 0.0, 0.0)
    out = rotate_about_y(out, roll_deg)
    return out


def floor_gap_mm(
    stance_foot,
    swing_foot,
    q_stance_deg: float,
    q_swing_deg: float,
    roll_deg: float,
    body_pitch_deg: float,
) -> float:
    stance = transform_foot(stance_foot, q_stance_deg, body_pitch_deg, roll_deg)
    swing = transform_foot(swing_foot, q_swing_deg, body_pitch_deg, roll_deg)
    return swing.BoundingBox().zmin - stance.BoundingBox().zmin


def touchdown_roots_deg(
    stance_foot,
    swing_foot,
    q_stance_deg: float,
    q_swing_deg: float,
    body_pitch_deg: float = 0.0,
    roll_min_deg: float = -25.0,
    roll_max_deg: float = 25.0,
    scan_step_deg: float = 0.25,
) -> list[float]:
    roots: list[float] = []
    x0 = roll_min_deg
    f0 = floor_gap_mm(
        stance_foot,
        swing_foot,
        q_stance_deg,
        q_swing_deg,
        x0,
        body_pitch_deg,
    )
    x = x0 + scan_step_deg
    while x <= roll_max_deg + 1e-12:
        f1 = floor_gap_mm(
            stance_foot,
            swing_foot,
            q_stance_deg,
            q_swing_deg,
            x,
            body_pitch_deg,
        )
        if f0 == 0.0 or f0 * f1 < 0.0:
            lo, hi = x - scan_step_deg, x
            flo = floor_gap_mm(
                stance_foot,
                swing_foot,
                q_stance_deg,
                q_swing_deg,
                lo,
                body_pitch_deg,
            )
            for _ in range(50):
                mid = (lo + hi) / 2.0
                fm = floor_gap_mm(
                    stance_foot,
                    swing_foot,
                    q_stance_deg,
                    q_swing_deg,
                    mid,
                    body_pitch_deg,
                )
                if flo * fm <= 0.0:
                    hi = mid
                else:
                    lo = mid
                    flo = fm
            root = (lo + hi) / 2.0
            if not roots or abs(root - roots[-1]) > 1e-5:
                roots.append(root)
        x0, f0 = x, f1
        x += scan_step_deg
    return roots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", type=Path)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--pitch", type=float, default=0.0)
    args = ap.parse_args()

    solids = cq.importers.importStep(str(args.step)).solids().vals()
    if len(solids) != 10:
        raise RuntimeError(f"Expected 10 STEP solids, got {len(solids)}")

    stance = solids[RIGHT_FOOT_ID]
    swing = solids[LEFT_FOOT_ID]
    geom = LegGeometry()
    q_stance_values = (-20.0, -15.0, -10.0, -5.0, 0.0)
    q_swing_values = (0.0, -2.5, -5.0, -7.5, -10.0, -12.5, -15.0, -17.5, -20.0)

    rows = []
    for qs in q_stance_values:
        for qw in q_swing_values:
            roots = touchdown_roots_deg(
                stance,
                swing,
                qs,
                qw,
                body_pitch_deg=args.pitch,
            )
            rows.append(
                {
                    "body_pitch_deg": args.pitch,
                    "q_stance_deg": qs,
                    "q_swing_deg": qw,
                    "ankle_travel_from_q0_mm": geom.ankle_travel_from_qmax_mm(qw),
                    "stride_fraction": geom.stride_fraction_from_qmax(qw),
                    "root_count": len(roots),
                    "touchdown_roll_deg": roots[0] if len(roots) == 1 else "",
                    "all_touchdown_roll_roots_deg": ";".join(f"{r:.9f}" for r in roots),
                }
            )

    fields = list(rows[0])
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    else:
        writer = csv.DictWriter(__import__("sys").stdout, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
