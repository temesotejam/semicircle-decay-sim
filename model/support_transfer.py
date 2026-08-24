"""Post-touchdown support-transfer kinematics.

This module deliberately contains only geometry-level relations that are
currently justified without guessing contact stiffness, damping, restitution,
or friction.

Coordinate convention
---------------------
- STEP X: lateral
- STEP Y: fore-aft (physical forward sign still unconfirmed)
- STEP Z: vertical
- body fore-aft pitch alpha: rotation about STEP X
- leg coordinate q: hip rotation about STEP X, q in [-20, 0] deg

Because the ankle is fixed, the absolute fore-aft pitch of the foot is

    beta_foot = alpha + q

The longitudinal sole is flat on a horizontal floor when beta_foot = 0, so the
flat-support target is q_flat = -alpha, provided that target lies inside the
mechanical hip stops.
"""
from __future__ import annotations

from dataclasses import dataclass

from model.leg_kinematics import LegGeometry


@dataclass(frozen=True)
class SupportTransferKinematics:
    leg: LegGeometry = LegGeometry()

    def foot_pitch_deg(self, q_deg: float, body_pitch_deg: float = 0.0) -> float:
        """Absolute longitudinal foot pitch relative to a horizontal floor."""
        return body_pitch_deg + q_deg

    def flat_target_q_deg(self, body_pitch_deg: float = 0.0) -> float:
        """Leg angle that would make the longitudinal sole exactly horizontal."""
        return -body_pitch_deg

    def flat_contact_feasible(self, body_pitch_deg: float = 0.0) -> bool:
        q = self.flat_target_q_deg(body_pitch_deg)
        return self.leg.within_hard_stops(q)

    def nearest_settle_q_deg(self, body_pitch_deg: float = 0.0) -> float:
        """Closest mechanically reachable q to the ideal flat-contact target."""
        q = self.flat_target_q_deg(body_pitch_deg)
        return min(self.leg.q_max_deg, max(self.leg.q_min_deg, q))

    def residual_foot_pitch_at_settle_deg(self, body_pitch_deg: float = 0.0) -> float:
        q = self.nearest_settle_q_deg(body_pitch_deg)
        return self.foot_pitch_deg(q, body_pitch_deg)

    def settle_progress(self, q_touch_deg: float, q_now_deg: float, body_pitch_deg: float = 0.0) -> float:
        """Normalized 0..1 progress from first contact toward the reachable settle target."""
        q_target = self.nearest_settle_q_deg(body_pitch_deg)
        denom = q_target - q_touch_deg
        if abs(denom) < 1e-12:
            return 1.0
        return min(1.0, max(0.0, (q_now_deg - q_touch_deg) / denom))

    @staticmethod
    def gravity_flattening_margin_mm(
        foot_pitch_deg: float,
        contact_y_mm: float,
        system_cg_y_mm: float,
    ) -> float:
        """Rigid-pivot gravity moment-arm sign check around a first-contact edge.

        Positive means the gravity torque around that *fixed contact point* has
        the sign that rotates the foot pitch toward zero.  This is only a local
        screening metric: the real robot has an internal hip DOF and a moving
        old support, so this value must not be treated as the full generalized
        support-transfer torque.
        """
        if abs(foot_pitch_deg) < 1e-12:
            return 0.0
        tau_over_mg_mm = contact_y_mm - system_cg_y_mm
        desired_sign = -1.0 if foot_pitch_deg > 0.0 else 1.0
        return desired_sign * tau_over_mg_mm
