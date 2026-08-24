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
from math import atan2, cos, degrees, hypot, radians, sin


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

    def ankle_y_displacement_mm(self, q_deg: float, reference_q_deg: float = 0.0) -> float:
        """Signed STEP-Y displacement of the ankle center from a reference pose."""
        y, _ = self.ankle_position_mm(q_deg)
        y_ref, _ = self.ankle_position_mm(reference_q_deg)
        return y - y_ref

    def ankle_travel_from_qmax_mm(self, q_deg: float) -> float:
        """Unsigned ankle-center travel from the q=0 hard stop.

        This is a geometry-only stride coordinate.  It is not yet the true
        ground-contact step length because the foot can first contact at its
        front/rear edge when body fore-aft pitch is nonzero.
        """
        if not self.within_hard_stops(q_deg):
            raise ValueError(f"q={q_deg} deg is outside [{self.q_min_deg}, {self.q_max_deg}]")
        return abs(self.ankle_y_displacement_mm(q_deg, self.q_max_deg))

    @property
    def ankle_y_travel_mm(self) -> float:
        return self.ankle_travel_from_qmax_mm(self.q_min_deg)

    def stride_fraction_from_qmax(self, q_deg: float) -> float:
        """0..1 fraction of the maximum ankle-center travel."""
        return self.ankle_travel_from_qmax_mm(q_deg) / self.ankle_y_travel_mm

    def q_for_ankle_travel_mm(self, travel_mm: float) -> float:
        """Invert the monotone q=0 -> q_min ankle-center travel relation."""
        if travel_mm < 0.0 or travel_mm > self.ankle_y_travel_mm:
            raise ValueError(
                f"travel={travel_mm} mm is outside [0, {self.ankle_y_travel_mm}]"
            )
        lo, hi = self.q_min_deg, self.q_max_deg
        for _ in range(70):
            mid = (lo + hi) / 2.0
            if self.ankle_travel_from_qmax_mm(mid) > travel_mm:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    def within_hard_stops(self, q_deg: float, tolerance_deg: float = 1e-9) -> bool:
        return self.q_min_deg - tolerance_deg <= q_deg <= self.q_max_deg + tolerance_deg
