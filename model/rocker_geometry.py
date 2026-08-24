"""Geometry-aware lateral rocker model.

The CAD/STEP file is used only for shape dimensions. Mass properties are not
read from CAD.

Coordinate convention
---------------------
X: lateral direction (front-view horizontal)
Y: fore-aft direction / cylinder axis
Z: vertical direction
The lateral rocking DOF is rotation about Y.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, sin, sqrt


@dataclass(frozen=True)
class RockerGeometry:
    """Minimal geometry for the two separated circular foot arcs."""

    radius_m: float = 0.150
    inner_edge_x_m: float = 0.005
    outer_edge_x_m: float = 0.045
    cg_height_upright_m: float = 0.128

    @property
    def center_height_upright_m(self) -> float:
        """Circle-center height when the two inner edges touch a flat floor."""
        return sqrt(self.radius_m**2 - self.inner_edge_x_m**2)

    @property
    def cg_below_circle_center_m(self) -> float:
        """Vertical circle-center to CG distance inferred from measured H.

        The default is the externally validated Model-B dynamic parameter;
        pass a height explicitly for historical Model-A comparisons.
        """
        return self.center_height_upright_m - self.cg_height_upright_m

    @property
    def theta_inner_rad(self) -> float:
        """Angle where the ideal tangent point reaches the inner arc edge."""
        return asin(self.inner_edge_x_m / self.radius_m)

    @property
    def theta_outer_rad(self) -> float:
        """Angle where the ideal tangent point reaches the outer arc edge."""
        return asin(self.outer_edge_x_m / self.radius_m)

    @property
    def center_missing_sagitta_m(self) -> float:
        """Height difference between a complete-circle bottom and inner edges."""
        return self.radius_m - self.center_height_upright_m

    def contact_mode(self, theta_rad: float) -> str:
        a = abs(theta_rad)
        if a == 0.0:
            return "double_inner_edge"
        if a < self.theta_inner_rad:
            return "single_inner_edge_pivot"
        if a <= self.theta_outer_rad:
            return "circular_arc"
        return "outer_edge_or_outside_cad_arc"

    def cg_height_m(self, theta_rad: float, cg_x_m: float = 0.0) -> float:
        """CG height above the floor for the ideal no-slip/pivot kinematics.

        cg_x_m is a lateral CG offset in body coordinates. Positive X is the
        positive/right CAD side. The symmetric default is zero.
        """
        mag = abs(theta_rad)
        side = 1.0 if theta_rad >= 0.0 else -1.0

        if mag <= self.theta_inner_rad:
            # Pivot around the lower-side inner edge. For positive/right roll,
            # the right inner edge (+a) is the support point.
            lever_x = self.inner_edge_x_m - side * cg_x_m
            return (
                self.cg_height_upright_m * cos(mag)
                + lever_x * sin(mag)
            )

        z_rel = self.cg_height_upright_m - self.center_height_upright_m
        return (
            self.radius_m
            - side * cg_x_m * sin(mag)
            + z_rel * cos(mag)
        )

    def delta_height_m(self, theta_rad: float, cg_x_m: float = 0.0) -> float:
        return self.cg_height_m(theta_rad, cg_x_m) - self.cg_height_upright_m

    def potential_delta_j(
        self,
        theta_rad: float,
        mass_kg: float,
        gravity_m_s2: float = 9.80665,
        cg_x_m: float = 0.0,
    ) -> float:
        return mass_kg * gravity_m_s2 * self.delta_height_m(theta_rad, cg_x_m)

    def complete_circle_delta_height_m(self, theta_rad: float) -> float:
        """Historical complete-circle approximation used for comparison."""
        return (
            (self.radius_m - self.cg_height_upright_m)
            * (1.0 - cos(abs(theta_rad)))
        )

    def complete_circle_potential_delta_j(
        self,
        theta_rad: float,
        mass_kg: float,
        gravity_m_s2: float = 9.80665,
    ) -> float:
        return (
            mass_kg
            * gravity_m_s2
            * self.complete_circle_delta_height_m(theta_rad)
        )
