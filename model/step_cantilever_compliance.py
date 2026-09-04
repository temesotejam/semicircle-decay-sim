"""STEP-derived angle-dependent foot compliance screening model.

This module keeps the rigid Model-B contact geometry, then adds a conservative
quasi-static correction for bending of the thin 1.5 mm rocker shell recovered
from the STEP source.  It is deliberately a reduced-order screening model, not
FEA and not a measured material model.

Geometry recovered from cad/Part_Studio_1.1.step:
- outer rocker radius R = 150 mm
- inner rocker radius = 148.5 mm -> radial shell thickness t = 1.5 mm
- rocker width along Y b = 56 mm
- inner contact edge |X| = 5 mm
- reinforced/root transition approximately |X| = 37 mm

The thin shell between the current contact point and the reinforced root is
approximated as a cantilever.  As the circular contact moves outward, its free
length decreases, so its vertical compliance falls as L(theta)^3.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import asin, sin

from .rocker_geometry import RockerGeometry


@dataclass(frozen=True)
class StepCantileverCompliance:
    geometry: RockerGeometry = RockerGeometry()
    root_x_m: float = 0.037
    shell_width_y_m: float = 0.056
    shell_thickness_m: float = 0.0015
    effective_youngs_modulus_pa: float = 12.0e9

    @property
    def root_angle_rad(self) -> float:
        return asin(self.root_x_m / self.geometry.radius_m)

    @property
    def shell_second_moment_m4(self) -> float:
        b = self.shell_width_y_m
        t = self.shell_thickness_m
        return b * t**3 / 12.0

    @property
    def max_free_arc_length_m(self) -> float:
        return self.geometry.radius_m * (
            self.root_angle_rad - self.geometry.theta_inner_rad
        )

    @property
    def inner_edge_vertical_stiffness_n_per_m(self) -> float:
        L = self.max_free_arc_length_m
        E = self.effective_youngs_modulus_pa
        I = self.shell_second_moment_m4
        return 3.0 * E * I / L**3

    def free_arc_length_m(self, theta_rad: float) -> float:
        """Thin-shell length between current circular contact and root.

        Below the rigid inner-edge tangent transition the contact remains at the
        inner edge.  Beyond the reinforced root the thin-strip contribution is
        taken as zero.
        """
        a = abs(theta_rad)
        contact_angle = max(a, self.geometry.theta_inner_rad)
        return max(
            0.0,
            self.geometry.radius_m * (self.root_angle_rad - contact_angle),
        )

    def single_support_compliance_m_per_n(self, theta_rad: float) -> float:
        """Vertical compliance of the thin rocker strip at the load point."""
        L = self.free_arc_length_m(theta_rad)
        if L <= 0.0:
            return 0.0
        E = self.effective_youngs_modulus_pa
        I = self.shell_second_moment_m4
        return L**3 / (3.0 * E * I)

    def _inner_dual_support_correction_j(
        self,
        theta_rad: float,
        total_normal_force_n: float,
    ) -> tuple[float, bool]:
        """Return correction and whether both inner-edge supports remain loaded."""
        k = self.inner_edge_vertical_stiffness_n_per_m
        a = self.geometry.inner_edge_x_m
        d0 = total_normal_force_n / (2.0 * k)
        dz = 2.0 * a * sin(abs(theta_rad))
        d_high = d0 - dz / 2.0
        d_low = d0 + dz / 2.0
        if d_high <= 0.0:
            return 0.0, False

        elastic = 0.5 * k * (d_high**2 + d_low**2)
        elastic0 = k * d0**2
        gravity = -total_normal_force_n * (d_low - d0)
        return gravity + (elastic - elastic0), True

    def compliance_potential_correction_j(
        self,
        theta_rad: float,
        mass_kg: float,
        gravity_m_s2: float = 9.80665,
    ) -> float:
        """Conservative quasi-static potential correction relative to upright.

        At theta=0 the weight is shared equally by the two inner edges.  While
        both stay loaded, their beam-tip stiffness is used for load sharing.
        After the high side unloads, the low side carries the full weight and
        the contact-dependent cantilever compliance is used.  The correction is
        the minimized gravity+strain-energy change relative to loaded upright.
        """
        total_n = mass_kg * gravity_m_s2
        if abs(theta_rad) < self.geometry.theta_inner_rad:
            corr, dual = self._inner_dual_support_correction_j(theta_rad, total_n)
            if dual:
                return corr

        c0 = 1.0 / self.inner_edge_vertical_stiffness_n_per_m
        c = self.single_support_compliance_m_per_n(theta_rad)
        return -0.5 * total_n**2 * c + 0.25 * total_n**2 * c0

    def total_potential_delta_j(
        self,
        theta_rad: float,
        mass_kg: float,
        gravity_m_s2: float = 9.80665,
    ) -> float:
        return self.geometry.potential_delta_j(
            theta_rad,
            mass_kg,
            gravity_m_s2,
        ) + self.compliance_potential_correction_j(
            theta_rad,
            mass_kg,
            gravity_m_s2,
        )
