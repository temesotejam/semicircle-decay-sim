"""Reduced-order two-foot compliance model for central rocking contact.

This is a screening model for deciding whether foot flexibility can be ignored.
It represents each inner foot region by a vertical linear spring. It is most
useful near upright where the two inner edges compete for contact. It does not
replace a shell/beam contact FEA and should not be extrapolated blindly over the
whole circular arc.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sin
from .rocker_geometry import RockerGeometry


@dataclass(frozen=True)
class ContactState:
    theta_rad: float
    mode: str
    left_force_n: float
    right_force_n: float
    left_compression_m: float
    right_compression_m: float
    low_side: str
    extra_settlement_from_upright_m: float


@dataclass(frozen=True)
class QuasiStaticCompliantContact:
    geometry: RockerGeometry = RockerGeometry()
    left_stiffness_n_per_m: float = 3000.0
    right_stiffness_n_per_m: float = 3000.0

    def _check(self) -> None:
        if self.left_stiffness_n_per_m <= 0 or self.right_stiffness_n_per_m <= 0:
            raise ValueError("foot stiffness values must be positive")

    def upright_compression_m(self, total_normal_force_n: float) -> float:
        self._check()
        return total_normal_force_n / (
            self.left_stiffness_n_per_m + self.right_stiffness_n_per_m
        )

    def solve(self, theta_rad: float, total_normal_force_n: float) -> ContactState:
        """Solve static load sharing for the two inner-edge spring supports."""
        self._check()
        if total_normal_force_n < 0:
            raise ValueError("total_normal_force_n must be non-negative")
        kL = self.left_stiffness_n_per_m
        kR = self.right_stiffness_n_per_m
        a = self.geometry.inner_edge_x_m
        delta_geom = 2.0 * a * sin(abs(theta_rad))
        d0 = self.upright_compression_m(total_normal_force_n)

        if theta_rad >= 0.0:
            # Positive roll: right inner edge is geometrically lower.
            dL = (total_normal_force_n - kR * delta_geom) / (kL + kR)
            if dL > 0.0:
                dR = dL + delta_geom
                mode = "dual_inner_edges"
            else:
                dL = 0.0
                dR = total_normal_force_n / kR
                mode = "right_only"
            low = "right"
        else:
            # Negative roll: left inner edge is geometrically lower.
            dR = (total_normal_force_n - kL * delta_geom) / (kL + kR)
            if dR > 0.0:
                dL = dR + delta_geom
                mode = "dual_inner_edges"
            else:
                dR = 0.0
                dL = total_normal_force_n / kL
                mode = "left_only"
            low = "left"

        fL = kL * dL
        fR = kR * dR
        low_compression = dR if low == "right" else dL
        return ContactState(
            theta_rad=theta_rad,
            mode=mode,
            left_force_n=fL,
            right_force_n=fR,
            left_compression_m=dL,
            right_compression_m=dR,
            low_side=low,
            extra_settlement_from_upright_m=low_compression - d0,
        )

    def compliance_potential_correction_j(
        self,
        theta_rad: float,
        mass_kg: float,
        gravity_m_s2: float = 9.80665,
    ) -> float:
        """Quasi-static correction relative to the loaded upright state."""
        total_n = mass_kg * gravity_m_s2
        s = self.solve(theta_rad, total_n)
        d0 = self.upright_compression_m(total_n)
        elastic0 = 0.5 * (
            self.left_stiffness_n_per_m + self.right_stiffness_n_per_m
        ) * d0**2
        elastic = (
            0.5 * self.left_stiffness_n_per_m * s.left_compression_m**2
            + 0.5 * self.right_stiffness_n_per_m * s.right_compression_m**2
        )
        gravity = -total_n * s.extra_settlement_from_upright_m
        return gravity + (elastic - elastic0)

    def screening_total_potential_delta_j(
        self,
        theta_rad: float,
        mass_kg: float,
        gravity_m_s2: float = 9.80665,
    ) -> float:
        return self.geometry.potential_delta_j(
            theta_rad, mass_kg, gravity_m_s2
        ) + self.compliance_potential_correction_j(
            theta_rad, mass_kg, gravity_m_s2
        )
