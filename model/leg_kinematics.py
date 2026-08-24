"""Rigid leg kinematics inferred from the audited STEP geometry.

This module contains only geometry that is currently treated as fixed:

- STEP X: lateral
- STEP Y: fore-aft
- STEP Z: vertical
- hip axis: X direction through Y=0, Z=-12 mm
- upper/lower leg connection: fixed
- ankle connection: fixed
- each leg + foot is one rigid body
- CAD hard-stop range: q in [-20 deg, 0 deg] relative to the STEP pose

The physical sign of STEP +Y versus walking-forward must still be confirmed on
hardware/video before calling q increasing/decreasing "forward" or "backward".
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, radians, sin, degrees


@dataclass(frozen=True)
class LegGeometry:
    hip_y_mm: float = 0.0
    hip_z_mm: float = -12.0
    fixed_bend_y_mm: float = 44.1672955930064
    fixed_bend_z_mm: float = -37.5
    ankle_y_mm: float = 11.2273845388904
    ankle_z_mm: float = -71.1398672165212
    q_min_deg: float = -20.0
    q_max_deg: float = 0.0

    @property
    def hip_to_fixed_bend_mm(self) -> float:
        return hypot(
            self.fixed_bend_y_mm - self.hip_y_mm,
            self.fixed_bend_z_mm - self.hip_z_mm,
        )

    @property
    def fixed_bend_to_ankle_mm(self) -> float:
        return hypot(
            self.ankle_y_mm - self.fixed_bend_y_mm,
            self.ankle_z_mm - self.fixed_bend_z_mm,
        )

    @property
    def hip_to_ankle_radius_mm(self) -> float:
        return hypot(
            self.ankle_y_mm - self.hip_y_mm,
            self.ankle_z_mm - self.hip_z_mm,
        )

    @property
    def cad_pose_angle_from_down_vertical_deg(self) -> float:
        dy = self.ankle_y_mm - self.hip_y_mm
        dz = self.ankle_z_mm - self.hip_z_mm
        return degrees(atan2(dy, -dz))

    @property
    def angle_range_from_down_vertical_deg(self) -> tuple[float, float]:
        psi0 = self.cad_pose_angle_from_down_vertical_deg
        return psi0 + self.q_min_deg, psi0 + self.q_max_deg

    def rotate_yz(self, y_mm: float, z_mm: float, q_deg: float) -> tuple[float, float]:
        """Rotate one body-fixed point around the hip X-axis."""
        a = radians(q_deg)
        y = y_mm - self.hip_y_mm
        z = z_mm - self.hip_z_mm
        return (
            self.hip_y_mm + y * cos(a) - z * sin(a),
            self.hip_z_mm + y * sin(a) + z * cos(a),
        )

    def ankle_position_mm(self, q_deg: float) -> tuple[float, float]:
        return self.rotate_yz(self.ankle_y_mm, self.ankle_z_mm, q_deg)

    @property
    def ankle_y_travel_mm(self) -> float:
        y0, _ = self.ankle_position_mm(self.q_max_deg)
        y1, _ = self.ankle_position_mm(self.q_min_deg)
        return abs(y0 - y1)

    def within_hard_stops(self, q_deg: float, tolerance_deg: float = 1e-9) -> bool:
        return self.q_min_deg - tolerance_deg <= q_deg <= self.q_max_deg + tolerance_deg
