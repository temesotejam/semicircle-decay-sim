"""Extract a geometry-only equal-density mass-distribution proxy from STEP.

Usage:
    python analysis/extract_leg_uniform_density_proxy.py "Part Studio 1.1.step"

This script does NOT claim the CAD volume centroid is the physical CG.  It is a
screening tool for the passive-swing hypothesis.  The actual printed parts,
fasteners, motor wiring, material/fill, and any added masses can shift the real
mass distribution.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq

HIP_Y_MM = 0.0
HIP_Z_MM = -12.0
LEFT_PARTS = {
    "upper": (0,),
    "lower": (6,),
    "foot": (7,),
    "leg_plus_foot": (0, 6, 7),
}


def fuse(solids, ids):
    out = solids[ids[0]]
    for idx in ids[1:]:
        out = out.fuse(solids[idx])
    return out


def shape_proxy(shape):
    volume = shape.Volume()
    c = shape.Center()
    moi = shape.matrixOfInertia(shape)
    y = c.y - HIP_Y_MM
    z = c.z - HIP_Z_MM
    r2 = y * y + z * z
    i_cm_x_per_mass = moi[0][0] / volume
    i_hip_x_per_mass = i_cm_x_per_mass + r2
    return {
        "volume_mm3": volume,
        "cg_rel_hip_y_mm": y,
        "cg_rel_hip_z_mm": z,
        "cg_radius_mm": math.sqrt(r2),
        "cg_angle_from_down_vertical_deg": math.degrees(math.atan2(y, -z)),
        "ix_cm_per_mass_mm2": i_cm_x_per_mass,
        "ix_hip_per_mass_mm2": i_hip_x_per_mass,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    solids = cq.importers.importStep(str(args.step)).solids().vals()
    if len(solids) != 10:
        raise RuntimeError(f"Expected 10 STEP solids, got {len(solids)}")

    result = {
        "warning": (
            "Equal-density STEP volume proxy only; do not use as final physical "
            "mass/CG/inertia without measured component masses."
        ),
        "hip_axis_yz_mm": [HIP_Y_MM, HIP_Z_MM],
        "left_parts": {
            name: shape_proxy(fuse(solids, ids)) for name, ids in LEFT_PARTS.items()
        },
    }
    group = result["left_parts"]["leg_plus_foot"]
    psi0 = group["cg_angle_from_down_vertical_deg"]
    result["passive_swing_screening"] = {
        "q_range_deg": [-20.0, 0.0],
        "gravity_torque_points_toward_qmin_over_entire_range_at_zero_body_pitch": (
            psi0 - 20.0 > 0.0
        ),
        "gravity_torque_zero_at_qmin_body_pitch_deg": -(psi0 - 20.0),
        "frictionless_energy_reachability_body_pitch_limit_deg": -(psi0 - 10.0),
    }

    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.json:
        args.json.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
