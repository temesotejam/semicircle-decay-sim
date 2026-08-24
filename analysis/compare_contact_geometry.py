"""Compare the historical complete-circle potential with the STEP-based gap model.

Run from repository root:
    python -m analysis.compare_contact_geometry
"""

from __future__ import annotations

from math import degrees, radians

from model.rocker_geometry import RockerGeometry


MASS_KG = 0.1997
G = 9.80665


def main() -> None:
    geom = RockerGeometry()

    print("STEP-based lateral rocker geometry")
    print(f"R                 = {geom.radius_m * 1e3:.3f} mm")
    print(f"half center gap   = {geom.inner_edge_x_m * 1e3:.3f} mm")
    print(f"full center gap   = {2 * geom.inner_edge_x_m * 1e3:.3f} mm")
    print(f"inner transition  = {degrees(geom.theta_inner_rad):.6f} deg")
    print(f"outer arc limit   = {degrees(geom.theta_outer_rad):.6f} deg")
    print(f"missing sagitta   = {geom.center_missing_sagitta_m * 1e3:.6f} mm")
    print()

    print(
        "angle_deg,mode,complete_circle_dh_mm,gap_model_dh_mm,"
        "complete_circle_U_mJ,gap_model_U_mJ,U_ratio"
    )
    angles_deg = [0.5, 1.0, 1.5, degrees(geom.theta_inner_rad), 3.0,
                  5.0, 6.5, 6.625, 7.0, 10.0, 15.0, 17.0,
                  degrees(geom.theta_outer_rad)]

    for angle_deg in angles_deg:
        theta = radians(angle_deg)
        dh_old = geom.complete_circle_delta_height_m(theta)
        dh_gap = geom.delta_height_m(theta)
        u_old = MASS_KG * G * dh_old
        u_gap = MASS_KG * G * dh_gap
        ratio = u_gap / u_old if u_old > 0.0 else float("nan")
        print(
            f"{angle_deg:.6f},{geom.contact_mode(theta)},"
            f"{dh_old * 1e3:.6f},{dh_gap * 1e3:.6f},"
            f"{u_old * 1e3:.6f},{u_gap * 1e3:.6f},{ratio:.6f}"
        )


if __name__ == "__main__":
    main()
