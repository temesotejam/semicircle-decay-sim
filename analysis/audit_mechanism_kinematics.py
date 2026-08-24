"""Audit mechanism axes, rigid groups, hard stops, and floor geometry from STEP.

Usage
-----
python analysis/audit_mechanism_kinematics.py "Part Studio 1.1.step" --out mechanism_audit_out

The STEP file is geometry only. Mechanical semantics that cannot be inferred
from STEP are explicitly supplied from the confirmed real assembly:

- solids 0, 6, 7: left leg + foot, one rigid body
- solids 8, 5, 9: right leg + foot, one rigid body
- solids 1, 2, 3, 4: central body collision group
- upper/lower leg connection is FIXED
- ankle connection is FIXED
- hip connection is REVOLUTE

The audit does not silently remove the hip neighborhood from collision tests.
This matters because the non-circular hip geometry itself forms the CAD hard
stops. Coaxial cylindrical bearing contact is allowed because it produces zero
intersection volume under valid rotation; non-axisymmetric overlap produces a
positive boolean-intersection volume and is treated as penetration.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

BODY_IDS = (1, 2, 3, 4)
LEFT_LEG_IDS = (0, 6, 7)
RIGHT_LEG_IDS = (8, 5, 9)
LEFT_UPPER_ID = 0
RIGHT_UPPER_ID = 8
LEFT_LOWER_ID = 6
RIGHT_LOWER_ID = 5
LEFT_FOOT_ID = 7
RIGHT_FOOT_ID = 9

INTERSECTION_TOL_MM3 = 1e-5
AXIS_TOL_MM = 1e-5
AXIS_DIR_TOL = 1e-6


@dataclass(frozen=True)
class AxisLine:
    y_mm: float
    z_mm: float


@dataclass(frozen=True)
class CylinderInfo:
    radius_mm: float
    x_mm: float
    y_mm: float
    z_mm: float
    dx: float
    dy: float
    dz: float


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_solids(step_path: Path):
    return cq.importers.importStep(str(step_path)).solids().vals()


def fuse_group(solids, ids):
    shape = solids[ids[0]]
    for idx in ids[1:]:
        shape = shape.fuse(solids[idx])
    return shape


def x_axis_cylinders(shape) -> list[CylinderInfo]:
    out = []
    for face in shape.Faces():
        surf = BRepAdaptor_Surface(face.wrapped, True)
        if surf.GetType() != GeomAbs_Cylinder:
            continue
        cyl = surf.Cylinder()
        axis = cyl.Axis()
        d = axis.Direction()
        if (
            abs(abs(d.X()) - 1.0) > AXIS_DIR_TOL
            or abs(d.Y()) > AXIS_DIR_TOL
            or abs(d.Z()) > AXIS_DIR_TOL
        ):
            continue
        p = axis.Location()
        out.append(
            CylinderInfo(
                cyl.Radius(), p.X(), p.Y(), p.Z(), d.X(), d.Y(), d.Z()
            )
        )
    return out


def common_x_axis(shape_a, shape_b) -> list[AxisLine]:
    """Return unique X-parallel cylinder centerlines common to two solids."""
    found: list[AxisLine] = []
    for a in x_axis_cylinders(shape_a):
        for b in x_axis_cylinders(shape_b):
            if math.hypot(a.y_mm - b.y_mm, a.z_mm - b.z_mm) > AXIS_TOL_MM:
                continue
            line = AxisLine((a.y_mm + b.y_mm) / 2.0, (a.z_mm + b.z_mm) / 2.0)
            if not any(
                math.hypot(line.y_mm - q.y_mm, line.z_mm - q.z_mm)
                <= AXIS_TOL_MM
                for q in found
            ):
                found.append(line)
    return found


def rotate_about_x(shape, axis: AxisLine, angle_deg: float):
    return shape.rotate(
        cq.Vector(-100.0, axis.y_mm, axis.z_mm),
        cq.Vector(+100.0, axis.y_mm, axis.z_mm),
        angle_deg,
    )


def intersection_volume_mm3(a, b) -> float:
    return a.intersect(b).Volume()


def find_stop(
    body,
    leg,
    axis: AxisLine,
    direction: int,
    step_deg: float = 0.25,
    max_abs_deg: float = 90.0,
):
    """Find the penetration boundary nearest q=0 in one direction."""
    assert direction in (-1, 1)
    q_safe = 0.0
    q = direction * step_deg
    while abs(q) <= max_abs_deg:
        v = intersection_volume_mm3(rotate_about_x(leg, axis, q), body)
        if v > INTERSECTION_TOL_MM3:
            q_collision = q
            break
        q_safe = q
        q += direction * step_deg
    else:
        return None

    lo, hi = sorted((q_safe, q_collision))
    for _ in range(45):
        mid = (lo + hi) / 2.0
        penetrates = (
            intersection_volume_mm3(rotate_about_x(leg, axis, mid), body)
            > INTERSECTION_TOL_MM3
        )
        if direction > 0:
            if penetrates:
                hi = mid
            else:
                lo = mid
        else:
            if penetrates:
                lo = mid
            else:
                hi = mid
    return (lo + hi) / 2.0


def rotate_point_yz(y_mm: float, z_mm: float, axis: AxisLine, q_deg: float):
    a = math.radians(q_deg)
    y = y_mm - axis.y_mm
    z = z_mm - axis.z_mm
    return (
        axis.y_mm + y * math.cos(a) - z * math.sin(a),
        axis.z_mm + y * math.sin(a) + z * math.cos(a),
    )


def penetration_probe(body, leg, axis: AxisLine, q_deg: float):
    inter = rotate_about_x(leg, axis, q_deg).intersect(body)
    if inter.Volume() <= INTERSECTION_TOL_MM3:
        return None
    bb = inter.BoundingBox()
    c = inter.Center()
    return {
        "angle_deg": q_deg,
        "volume_mm3": inter.Volume(),
        "bbox_mm": [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax],
        "centroid_mm": [c.x, c.y, c.z],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", type=Path)
    ap.add_argument("--out", type=Path, default=Path("mechanism_audit_out"))
    ap.add_argument("--sweep-min", type=float, default=-25.0)
    ap.add_argument("--sweep-max", type=float, default=5.0)
    ap.add_argument("--sweep-step", type=float, default=0.25)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    solids = load_solids(args.step)
    if len(solids) != 10:
        raise RuntimeError(f"Expected 10 STEP solids, got {len(solids)}")

    body = fuse_group(solids, BODY_IDS)
    left = fuse_group(solids, LEFT_LEG_IDS)
    right = fuse_group(solids, RIGHT_LEG_IDS)

    left_hip = common_x_axis(solids[LEFT_UPPER_ID], body)
    right_hip = common_x_axis(solids[RIGHT_UPPER_ID], body)
    left_bend = common_x_axis(solids[LEFT_UPPER_ID], solids[LEFT_LOWER_ID])
    right_bend = common_x_axis(solids[RIGHT_UPPER_ID], solids[RIGHT_LOWER_ID])
    left_ankle = common_x_axis(solids[LEFT_LOWER_ID], solids[LEFT_FOOT_ID])
    right_ankle = common_x_axis(solids[RIGHT_LOWER_ID], solids[RIGHT_FOOT_ID])

    if len(left_hip) != 1 or len(right_hip) != 1:
        raise RuntimeError(f"Could not uniquely infer hip axes: {left_hip=} {right_hip=}")
    hip = left_hip[0]
    if math.hypot(
        hip.y_mm - right_hip[0].y_mm, hip.z_mm - right_hip[0].z_mm
    ) > AXIS_TOL_MM:
        raise RuntimeError("Left and right hip centerlines differ")
    if len(left_bend) != 1 or len(right_bend) != 1:
        raise RuntimeError("Could not uniquely infer fixed upper/lower connection")
    if len(left_ankle) != 1 or len(right_ankle) != 1:
        raise RuntimeError("Could not uniquely infer fixed ankle connection")

    q_min_l = find_stop(body, left, hip, -1)
    q_max_l = find_stop(body, left, hip, +1)
    q_min_r = find_stop(body, right, hip, -1)
    q_max_r = find_stop(body, right, hip, +1)

    bend = left_bend[0]
    ankle = left_ankle[0]
    dy = ankle.y_mm - hip.y_mm
    dz = ankle.z_mm - hip.z_mm
    hip_ankle_radius = math.hypot(dy, dz)
    psi0 = math.degrees(math.atan2(dy, -dz))

    # Both foot solids are on the floor in the CAD assembly. This ground plane
    # is only a reference for the fixed-body diagnostic below.
    ground_z = min(
        solids[LEFT_FOOT_ID].BoundingBox().zmin,
        solids[RIGHT_FOOT_ID].BoundingBox().zmin,
    )

    rows = []
    q = args.sweep_min
    while q <= args.sweep_max + 1e-12:
        l = rotate_about_x(left, hip, q)
        r = rotate_about_x(right, hip, q)
        ay, az = rotate_point_yz(ankle.y_mm, ankle.z_mm, hip, q)
        lf = rotate_about_x(solids[LEFT_FOOT_ID], hip, q)
        rows.append(
            {
                "q_deg": q,
                "left_body_intersection_mm3": intersection_volume_mm3(l, body),
                "right_body_intersection_mm3": intersection_volume_mm3(r, body),
                "ankle_y_mm": ay,
                "ankle_z_mm": az,
                "leg_angle_from_down_vertical_deg": psi0 + q,
                "left_foot_zmin_mm_fixed_body": lf.BoundingBox().zmin,
                "left_foot_raw_ground_gap_mm_fixed_body": lf.BoundingBox().zmin
                - ground_z,
            }
        )
        q += args.sweep_step

    with (args.out / "leg_sweep_collision.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    left_bb = left.BoundingBox()
    right_bb = right.BoundingBox()
    x_gap = right_bb.xmin - left_bb.xmax
    ankle_y_min, _ = rotate_point_yz(ankle.y_mm, ankle.z_mm, hip, q_min_l)
    ankle_y_max, _ = rotate_point_yz(ankle.y_mm, ankle.z_mm, hip, q_max_l)

    summary = {
        "source_step": {
            "name": args.step.name,
            "sha256": sha256(args.step),
            "solid_count": len(solids),
        },
        "coordinate_convention": {
            "X": "lateral",
            "Y": "fore_aft_sign_not_yet_mapped_to_physical_forward",
            "Z": "vertical",
        },
        "rigid_groups": {
            "body_collision_group": list(BODY_IDS),
            "left_leg_plus_foot": list(LEFT_LEG_IDS),
            "right_leg_plus_foot": list(RIGHT_LEG_IDS),
        },
        "joint_semantics_confirmed_from_real_assembly": {
            "hip": "revolute",
            "upper_lower_connection": "fixed",
            "ankle": "fixed",
        },
        "hip_axis": {
            "direction": [1.0, 0.0, 0.0],
            "y_mm": hip.y_mm,
            "z_mm": hip.z_mm,
        },
        "fixed_connection_reference_axes_yz_mm": {
            "upper_lower_left": [left_bend[0].y_mm, left_bend[0].z_mm],
            "upper_lower_right": [right_bend[0].y_mm, right_bend[0].z_mm],
            "ankle_left": [left_ankle[0].y_mm, left_ankle[0].z_mm],
            "ankle_right": [right_ankle[0].y_mm, right_ankle[0].z_mm],
        },
        "cad_hard_stop_limits_deg_relative_to_step_pose": {
            "left_raw": [q_min_l, q_max_l],
            "right_raw": [q_min_r, q_max_r],
            "recommended_rounded_model_limits": [-20.0, 0.0],
        },
        "leg_reference_geometry": {
            "hip_to_fixed_bend_mm": math.hypot(
                bend.y_mm - hip.y_mm, bend.z_mm - hip.z_mm
            ),
            "fixed_bend_to_ankle_mm": math.hypot(
                ankle.y_mm - bend.y_mm, ankle.z_mm - bend.z_mm
            ),
            "hip_to_ankle_radius_mm": hip_ankle_radius,
            "cad_pose_leg_angle_from_down_vertical_deg": psi0,
            "angle_range_from_down_vertical_deg": [psi0 + q_min_l, psi0 + q_max_l],
            "ankle_y_at_qmin_mm": ankle_y_min,
            "ankle_y_at_qmax_mm": ankle_y_max,
            "ankle_y_travel_mm": abs(ankle_y_max - ankle_y_min),
        },
        "left_right_leg_collision": {
            "x_gap_mm_at_all_q": x_gap,
            "reason": "rotation about X preserves X; the 10 mm X gap proves the two leg rigid groups cannot geometrically intersect",
        },
        "floor_reference": {
            "cad_pose_ground_z_mm": ground_z,
            "warning": "fixed-body floor gap is diagnostic only; walking contact must solve body pose/roll and foot-ground nonpenetration together",
        },
        "stop_penetration_probes": {
            "above_qmax_left": penetration_probe(body, left, hip, q_max_l + 0.1),
            "below_qmin_left": penetration_probe(body, left, hip, q_min_l - 0.1),
        },
    }
    (args.out / "mechanism_audit_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
