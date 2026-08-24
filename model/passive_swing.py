"""Passive swing-leg screening model.

The physical idea tested here is:

1. the roll motion unloads one leg,
2. the unloaded rigid leg+foot assembly swings about its X-axis hip joint under
   gravity,
3. support can be transferred before the swing leg reaches the mechanical
   q=-20 deg stop, giving a shorter step than the maximum stop-to-stop travel.

The default parameter factory is deliberately named ``uniform_step_proxy``.
It uses the volume centroid and inertia of the STEP leg+foot rigid group under
an *equal-density* assumption.  It is useful for gravity-direction and time-
scale screening, but it is not a measured physical mass model.  Actual part
masses, joint friction, hip acceleration, and stop restitution remain to be
measured.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, radians, sin
from typing import Callable

G_M_S2 = 9.80665


@dataclass(frozen=True)
class PassiveSwingParameters:
    # CG relative to the hip axis in the body-fixed YZ plane.
    cg_y_mm: float
    cg_z_rel_hip_mm: float

    # I_hip / m.  Because gravity torque and inertia both scale with mass,
    # passive q(t) can be screened without choosing an arbitrary density.
    inertia_per_mass_about_hip_mm2: float

    q_min_deg: float = -20.0
    q_max_deg: float = 0.0
    source: str = "parameterized"

    @property
    def cg_radius_mm(self) -> float:
        return hypot(self.cg_y_mm, self.cg_z_rel_hip_mm)

    @property
    def cg_angle_from_down_vertical_deg(self) -> float:
        return degrees(atan2(self.cg_y_mm, -self.cg_z_rel_hip_mm))

    @property
    def pitch_for_zero_gravity_torque_at_qmin_deg(self) -> float:
        """Body pitch at which gravity torque is zero exactly at q_min."""
        return -(self.cg_angle_from_down_vertical_deg + self.q_min_deg)

    @property
    def pitch_energy_reachability_limit_deg(self) -> float:
        """Frictionless pitch boundary for reaching q_min from rest at q=0.

        For the present geometry this is the pitch where the potential at
        q_min equals the potential at q=0.  More negative pitch makes q_min
        energetically uphill from the released q=0 state.
        """
        return -(self.cg_angle_from_down_vertical_deg + self.q_min_deg / 2.0)

    def gravity_qdd_rad_s2(self, q_rad: float, body_pitch_rad: float = 0.0) -> float:
        """Relative-joint angular acceleration for a fixed/nonaccelerating hip.

        Body pitch is allowed as a constant orientation offset.  A time-varying
        body pitch would add base angular-acceleration terms and is intentionally
        outside this first screening model.
        """
        beta = q_rad + body_pitch_rad
        y_global_m = (
            self.cg_y_mm * cos(beta) - self.cg_z_rel_hip_mm * sin(beta)
        ) * 1e-3
        i_over_m_m2 = self.inertia_per_mass_about_hip_mm2 * 1e-6
        return -G_M_S2 * y_global_m / i_over_m_m2

    def potential_per_mass_j_per_kg(
        self, q_rad: float, body_pitch_rad: float = 0.0
    ) -> float:
        beta = q_rad + body_pitch_rad
        z_global_m = (
            self.cg_y_mm * sin(beta) + self.cg_z_rel_hip_mm * cos(beta)
        ) * 1e-3
        return G_M_S2 * z_global_m


def uniform_step_proxy() -> PassiveSwingParameters:
    """Return the equal-density STEP shape proxy for one leg+foot rigid group."""
    return PassiveSwingParameters(
        cg_y_mm=21.88279175285118,
        cg_z_rel_hip_mm=-34.02412489617628,
        inertia_per_mass_about_hip_mm2=2532.0140795711786,
        source=(
            "uniform-density STEP volume proxy for solids 0+6+7 "
            "(mirrored by solids 8+5+9)"
        ),
    )


def _rk4_step(
    p: PassiveSwingParameters,
    q: float,
    qdot: float,
    dt: float,
    body_pitch_rad: float,
) -> tuple[float, float]:
    def f(qi: float, wi: float) -> tuple[float, float]:
        return wi, p.gravity_qdd_rad_s2(qi, body_pitch_rad)

    k1 = f(q, qdot)
    k2 = f(q + 0.5 * dt * k1[0], qdot + 0.5 * dt * k1[1])
    k3 = f(q + 0.5 * dt * k2[0], qdot + 0.5 * dt * k2[1])
    k4 = f(q + dt * k3[0], qdot + dt * k3[1])

    return (
        q + dt * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6.0,
        qdot + dt * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6.0,
    )


def simulate_until_stop(
    p: PassiveSwingParameters | None = None,
    q0_deg: float = 0.0,
    qdot0_dps: float = 0.0,
    body_pitch_deg: float = 0.0,
    dt_s: float = 1e-4,
    max_time_s: float = 2.0,
) -> tuple[list[tuple[float, float, float]], tuple[float, float] | None]:
    """Integrate the ideal passive swing until q_min.

    Returns a time history ``(t_s, q_deg, qdot_dps)`` and, if reached, the
    pre-impact ``(impact_time_s, impact_qdot_dps)``.  The stop response itself
    is not modeled because restitution/compliance are not measured.
    """
    p = p or uniform_step_proxy()
    q = radians(q0_deg)
    qdot = radians(qdot0_dps)
    pitch = radians(body_pitch_deg)
    q_min = radians(p.q_min_deg)
    t = 0.0
    rows = [(0.0, q0_deg, qdot0_dps)]

    while t < max_time_s:
        q_next, qdot_next = _rk4_step(p, q, qdot, dt_s, pitch)
        if q_next <= q_min:
            frac = (q - q_min) / (q - q_next) if q != q_next else 0.0
            impact_t = t + frac * dt_s
            impact_qdot = qdot + frac * (qdot_next - qdot)
            rows.append((impact_t, p.q_min_deg, degrees(impact_qdot)))
            return rows, (impact_t, degrees(impact_qdot))

        t += dt_s
        q, qdot = q_next, qdot_next
        rows.append((t, degrees(q), degrees(qdot)))

    return rows, None


def interpolate_state_at_q(
    rows: list[tuple[float, float, float]], q_target_deg: float
) -> tuple[float, float]:
    """Return (time_s, qdot_dps) at a monotone decreasing q target."""
    if q_target_deg == rows[0][1]:
        return rows[0][0], rows[0][2]
    for a, b in zip(rows[:-1], rows[1:]):
        t0, q0, w0 = a
        t1, q1, w1 = b
        if q0 >= q_target_deg >= q1:
            frac = (q0 - q_target_deg) / (q0 - q1) if q0 != q1 else 0.0
            return t0 + frac * (t1 - t0), w0 + frac * (w1 - w0)
    raise ValueError(f"q={q_target_deg} deg was not reached by the supplied trajectory")
