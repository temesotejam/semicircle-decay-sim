"""First-order compliance screening for the thin printed rocker feet.

This module intentionally does *not* assign a material to the STEP file.  The
STEP model contributes geometry only.  Young's modulus, damping and correction
factors are external parameters to measure or sweep.

The beam formula is an order-of-magnitude screen, not a replacement for FEA:
we approximate the thin circular strip between the inner contact edge and the
start of the reinforced/root region as a cantilever of rectangular section.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import asin, pi, sqrt


@dataclass(frozen=True)
class FootArcSection:
    """Geometry extracted from the STEP foot arc."""

    outer_radius_m: float = 0.150
    inner_radius_m: float = 0.1485
    arc_width_y_m: float = 0.056
    inner_edge_x_m: float = 0.005
    reinforced_start_x_m: float = 0.037

    @property
    def radial_thickness_m(self) -> float:
        return self.outer_radius_m - self.inner_radius_m

    @property
    def inner_edge_angle_rad(self) -> float:
        return asin(self.inner_edge_x_m / self.outer_radius_m)

    @property
    def reinforced_start_angle_rad(self) -> float:
        return asin(self.reinforced_start_x_m / self.outer_radius_m)

    @property
    def free_span_arc_m(self) -> float:
        return self.outer_radius_m * (
            self.reinforced_start_angle_rad - self.inner_edge_angle_rad
        )

    @property
    def second_moment_m4(self) -> float:
        """Rectangular-section I for bending through the radial thickness."""
        t = self.radial_thickness_m
        return self.arc_width_y_m * t**3 / 12.0

    def cantilever_tip_stiffness_n_per_m(
        self,
        youngs_modulus_pa: float,
        stiffness_correction: float = 1.0,
    ) -> float:
        """Return 3EI/L^3 times an explicit geometry/print correction factor."""
        if youngs_modulus_pa <= 0:
            raise ValueError("youngs_modulus_pa must be positive")
        if stiffness_correction <= 0:
            raise ValueError("stiffness_correction must be positive")
        L = self.free_span_arc_m
        return (
            stiffness_correction
            * 3.0
            * youngs_modulus_pa
            * self.second_moment_m4
            / L**3
        )

    @staticmethod
    def tip_deflection_m(force_n: float, stiffness_n_per_m: float) -> float:
        if stiffness_n_per_m <= 0:
            raise ValueError("stiffness_n_per_m must be positive")
        return force_n / stiffness_n_per_m

    def symmetric_double_support_limit_rad(
        self,
        total_normal_force_n: float,
        per_foot_stiffness_n_per_m: float,
    ) -> float:
        """Screening estimate for the angle where the high foot unloads.

        With two identical vertical tip springs separated by 2*a, their
        undeformed tip-height difference is approximately 2*a*sin(theta).
        Both contacts can remain compressed while this difference is no larger
        than F_total/k. This is only a central-contact approximation.
        """
        if per_foot_stiffness_n_per_m <= 0:
            raise ValueError("per_foot_stiffness_n_per_m must be positive")
        arg = total_normal_force_n / (
            2.0 * self.inner_edge_x_m * per_foot_stiffness_n_per_m
        )
        if arg >= 1.0:
            return pi / 2.0
        if arg <= -1.0:
            return -pi / 2.0
        return asin(arg)

    def symmetric_upright_stability_stiffness_n_per_m(
        self,
        mass_kg: float,
        cg_height_m: float,
        gravity_m_s2: float = 9.80665,
    ) -> float:
        """Critical stiffness in the simplified two-tip support model.

        Linearization gives U ~= (k*a^2 - m*g*H/2)*theta^2, so the simplified
        model is locally restoring at upright only when k > m*g*H/(2*a^2).
        This is a diagnostic lower bound, not a material property.
        """
        if mass_kg <= 0 or cg_height_m <= 0:
            raise ValueError("mass_kg and cg_height_m must be positive")
        a = self.inner_edge_x_m
        return mass_kg * gravity_m_s2 * cg_height_m / (2.0 * a**2)

    def first_cantilever_frequency_hz(
        self,
        youngs_modulus_pa: float,
        density_kg_m3: float,
    ) -> float:
        """Euler-Bernoulli first-mode frequency for the same screening beam."""
        if density_kg_m3 <= 0:
            raise ValueError("density_kg_m3 must be positive")
        beta1 = 1.875104068711961
        L = self.free_span_arc_m
        area = self.arc_width_y_m * self.radial_thickness_m
        return (
            beta1**2
            / (2.0 * pi * L**2)
            * sqrt(
                youngs_modulus_pa * self.second_moment_m4
                / (density_kg_m3 * area)
            )
        )


@dataclass(frozen=True)
class FootCompliance:
    """Measured/effective per-foot compliance parameters for later fitting."""

    stiffness_n_per_m: float
    damping_n_s_per_m: float = 0.0

    def force_n(
        self, compression_m: float, compression_rate_m_s: float = 0.0
    ) -> float:
        if compression_m <= 0.0:
            return 0.0
        return max(
            0.0,
            self.stiffness_n_per_m * compression_m
            + self.damping_n_s_per_m * compression_rate_m_s,
        )
