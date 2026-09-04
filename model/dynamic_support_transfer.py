"""Dynamic left/right support-transfer screening model for lateral rocking.

Model B changes the active inner-edge support instantaneously with roll sign.
This reduced model introduces one state, support_balance s in [-1,+1]:

  s=-1 : left inner support carries the central-contact resultant
  s= 0 : equal left/right load share
  s=+1 : right inner support carries the central-contact resultant

Near upright, the equilibrium balance moves continuously toward equal sharing
and s follows it with a first-order time constant.  Outside the central region
the rigid STEP circular-arc torque is retained.

This is a screening model.  It does not claim that the real normal forces are
exactly linear springs or that the support resultant alone captures impact,
slip, or structural hysteresis.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin

from .rocker_geometry import RockerGeometry


@dataclass(frozen=True)
class DynamicSupportTransfer:
    geometry: RockerGeometry = RockerGeometry()
    transfer_start_rad: float = 0.0
    transfer_tau_s: float = 0.0

    def equilibrium_support_balance(self, theta_rad: float) -> float:
        """Quasi-static desired left/right load balance.

        transfer_start_rad is the absolute roll angle at which dual-support
        load redistribution begins while approaching upright.  A value of zero
        reproduces the rigid Model-B side choice for every nonzero angle.
        """
        if theta_rad == 0.0:
            return 0.0
        side = 1.0 if theta_rad > 0.0 else -1.0
        a = abs(theta_rad)
        if self.transfer_start_rad <= 0.0 or a >= self.transfer_start_rad:
            return side
        return theta_rad / self.transfer_start_rad

    def support_rate(self, theta_rad: float, support_balance: float) -> float:
        target = self.equilibrium_support_balance(theta_rad)
        if self.transfer_tau_s <= 0.0:
            return 0.0
        return (target - support_balance) / self.transfer_tau_s

    def central_contact_torque_nm(
        self,
        theta_rad: float,
        support_balance: float,
        mass_kg: float,
        gravity_m_s2: float = 9.80665,
    ) -> float:
        """Gravity/contact generalized torque for the central support region."""
        h = self.geometry.cg_height_upright_m
        a = self.geometry.inner_edge_x_m
        return mass_kg * gravity_m_s2 * (
            h * sin(theta_rad) - a * support_balance * cos(theta_rad)
        )

    def circular_arc_torque_nm(
        self,
        theta_rad: float,
        mass_kg: float,
        gravity_m_s2: float = 9.80665,
    ) -> float:
        d = self.geometry.cg_below_circle_center_m
        return -mass_kg * gravity_m_s2 * d * sin(theta_rad)

    def gravity_torque_nm(
        self,
        theta_rad: float,
        support_balance: float,
        mass_kg: float,
        gravity_m_s2: float = 9.80665,
    ) -> float:
        if abs(theta_rad) > self.geometry.theta_inner_rad:
            return self.circular_arc_torque_nm(theta_rad, mass_kg, gravity_m_s2)
        return self.central_contact_torque_nm(
            theta_rad, support_balance, mass_kg, gravity_m_s2
        )

    def instantaneous_support_balance(self, theta_rad: float) -> float:
        """Value used when tau=0 to avoid a numerically stiff support state."""
        return self.equilibrium_support_balance(theta_rad)
