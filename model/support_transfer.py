"""Post-touchdown support-transfer kinematics and first dynamics screening.

The geometry part contains only relations that are already justified without
contact coefficients.  The dynamics proxy deliberately uses one uniform STEP
density scaled to the measured total mass (199.7 g), zero hip friction, and a
fixed body fore-aft pitch.  It is therefore a direction/time-scale screening,
not a final physical prediction.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, degrees, pi, radians, sin

from model.leg_kinematics import LegGeometry

G = 9.80665


@dataclass(frozen=True)
class SupportTransferKinematics:
    leg: LegGeometry = LegGeometry()

    def foot_pitch_deg(self, q_deg: float, body_pitch_deg: float = 0.0) -> float:
        """Absolute longitudinal foot pitch beta=alpha+q relative to floor."""
        return body_pitch_deg + q_deg

    def flat_target_q_deg(self, body_pitch_deg: float = 0.0) -> float:
        return -body_pitch_deg

    def flat_contact_feasible(self, body_pitch_deg: float = 0.0) -> bool:
        return self.leg.within_hard_stops(self.flat_target_q_deg(body_pitch_deg))

    def nearest_settle_q_deg(self, body_pitch_deg: float = 0.0) -> float:
        q = self.flat_target_q_deg(body_pitch_deg)
        return min(self.leg.q_max_deg, max(self.leg.q_min_deg, q))

    def residual_foot_pitch_at_settle_deg(self, body_pitch_deg: float = 0.0) -> float:
        return self.foot_pitch_deg(self.nearest_settle_q_deg(body_pitch_deg), body_pitch_deg)

    def settle_progress(self, q_touch_deg: float, q_now_deg: float, body_pitch_deg: float = 0.0) -> float:
        q_target = self.nearest_settle_q_deg(body_pitch_deg)
        denom = q_target - q_touch_deg
        if abs(denom) < 1e-12:
            return 1.0
        return min(1.0, max(0.0, (q_now_deg - q_touch_deg) / denom))


@dataclass(frozen=True)
class UniformDensitySupportTransferProxy:
    """1-DOF settling proxy after the old support has been unloaded.

    Assumptions
    -----------
    - new foot keeps its first-contact fore/aft sole edge fixed on the floor;
    - body pitch alpha is a fixed parameter;
    - new leg+foot rotates at the hip;
    - old leg is airborne and held at q_old for this first screening;
    - all STEP solids have one density, scaled to total measured mass 199.7 g.
    """

    kin: SupportTransferKinematics = SupportTransferKinematics()
    total_mass_kg: float = 0.1997

    # STEP volume groups [mm^3]
    body_volume_mm3: float = 115361.08804635501
    leg_volume_mm3: float = 22742.89781212662
    total_volume_mm3: float = 160846.8836706085

    # STEP volume centroids [mm]
    body_cg_y_mm: float = 13.139463093332415
    body_cg_z_mm: float = 33.65672016206197
    leg_cg_y_mm: float = 21.882791752851226
    leg_cg_z_mm: float = -46.02412489617681

    # Sole/hip geometry [mm]
    hip_y_mm: float = 0.0
    hip_z_mm: float = -12.0
    sole_front_y_mm: float = 39.227384538890405
    sole_rear_y_mm: float = -16.772615461109613
    sole_bottom_z_mm: float = -92.96563050962881

    # STEP uniform-density proxy I_x,cm / m for one leg+foot [mm^2]
    leg_ix_cm_per_mass_mm2: float = 2532.0140795711786
    default_old_leg_q_deg: float = -20.0

    @property
    def body_mass_kg(self) -> float:
        return self.total_mass_kg * self.body_volume_mm3 / self.total_volume_mm3

    @property
    def leg_mass_kg(self) -> float:
        return self.total_mass_kg * self.leg_volume_mm3 / self.total_volume_mm3

    def _rot(self, y_mm: float, z_mm: float, angle_deg: float) -> tuple[float, float]:
        a = radians(angle_deg)
        y = y_mm - self.hip_y_mm
        z = z_mm - self.hip_z_mm
        return (
            self.hip_y_mm + y * cos(a) - z * sin(a),
            self.hip_z_mm + y * sin(a) + z * cos(a),
        )

    def _contact_edge_y_mm(self, q_touch_deg: float, body_pitch_deg: float) -> float:
        beta = self.kin.foot_pitch_deg(q_touch_deg, body_pitch_deg)
        return self.sole_front_y_mm if beta <= 0.0 else self.sole_rear_y_mm

    def pose(
        self,
        q_new_deg: float,
        q_touch_deg: float,
        body_pitch_deg: float = 0.0,
        q_old_deg: float | None = None,
    ) -> dict[str, object]:
        if q_old_deg is None:
            q_old_deg = self.default_old_leg_q_deg
        edge_y = self._contact_edge_y_mm(q_touch_deg, body_pitch_deg)

        # New-foot first-contact edge: leg-relative q, then common body pitch.
        ey, ez = self._rot(edge_y, self.sole_bottom_z_mm, q_new_deg)
        ey, ez = self._rot(ey, ez, body_pitch_deg)
        ty, tz = -ey, -ez

        by, bz = self._rot(self.body_cg_y_mm, self.body_cg_z_mm, body_pitch_deg)
        ny, nz = self._rot(self.leg_cg_y_mm, self.leg_cg_z_mm, q_new_deg)
        ny, nz = self._rot(ny, nz, body_pitch_deg)
        oy, oz = self._rot(self.leg_cg_y_mm, self.leg_cg_z_mm, q_old_deg)
        oy, oz = self._rot(oy, oz, body_pitch_deg)

        return {
            "translation_yz_mm": (ty, tz),
            "body_cg_yz_mm": (by + ty, bz + tz),
            "new_leg_cg_yz_mm": (ny + ty, nz + tz),
            "old_leg_cg_yz_mm": (oy + ty, oz + tz),
            "contact_edge_y_mm": edge_y,
        }

    def potential_j(
        self,
        q_new_deg: float,
        q_touch_deg: float,
        body_pitch_deg: float = 0.0,
        q_old_deg: float | None = None,
    ) -> float:
        p = self.pose(q_new_deg, q_touch_deg, body_pitch_deg, q_old_deg)
        bz = p["body_cg_yz_mm"][1]  # type: ignore[index]
        nz = p["new_leg_cg_yz_mm"][1]  # type: ignore[index]
        oz = p["old_leg_cg_yz_mm"][1]  # type: ignore[index]
        return G * (
            self.body_mass_kg * bz
            + self.leg_mass_kg * nz
            + self.leg_mass_kg * oz
        ) / 1000.0

    def effective_inertia_kgm2(
        self,
        q_new_deg: float,
        q_touch_deg: float,
        body_pitch_deg: float = 0.0,
        q_old_deg: float | None = None,
    ) -> float:
        h = 1e-4
        p1 = self.pose(q_new_deg + h, q_touch_deg, body_pitch_deg, q_old_deg)
        p0 = self.pose(q_new_deg - h, q_touch_deg, body_pitch_deg, q_old_deg)
        fac = (180.0 / pi) / (2.0 * h) / 1000.0  # d(mm)/d(rad) -> m/rad
        derivs = []
        for key in ("body_cg_yz_mm", "new_leg_cg_yz_mm", "old_leg_cg_yz_mm"):
            y1, z1 = p1[key]  # type: ignore[misc]
            y0, z0 = p0[key]  # type: ignore[misc]
            derivs.append(((y1-y0)*fac, (z1-z0)*fac))
        db, dn, do = derivs
        i_new = self.leg_mass_kg * self.leg_ix_cm_per_mass_mm2 * 1e-6
        return (
            self.body_mass_kg * (db[0]**2 + db[1]**2)
            + self.leg_mass_kg * (dn[0]**2 + dn[1]**2)
            + self.leg_mass_kg * (do[0]**2 + do[1]**2)
            + i_new
        )

    def energy_drop_to_settle_mj(
        self,
        q_touch_deg: float,
        body_pitch_deg: float = 0.0,
        q_old_deg: float | None = None,
    ) -> float:
        qf = self.kin.nearest_settle_q_deg(body_pitch_deg)
        return 1000.0 * (
            self.potential_j(qf, q_touch_deg, body_pitch_deg, q_old_deg)
            - self.potential_j(q_touch_deg, q_touch_deg, body_pitch_deg, q_old_deg)
        )

    def simulate_frictionless_settle(
        self,
        q_touch_deg: float,
        body_pitch_deg: float = 0.0,
        q_old_deg: float | None = None,
        dt_s: float = 1e-5,
        max_s: float = 2.0,
    ) -> dict[str, float | bool]:
        q_target_deg = self.kin.nearest_settle_q_deg(body_pitch_deg)
        if abs(q_target_deg - q_touch_deg) < 1e-12:
            return {
                "flat_reachable": self.kin.flat_contact_feasible(body_pitch_deg),
                "q_settle_deg": q_target_deg,
                "residual_foot_pitch_deg": self.kin.residual_foot_pitch_at_settle_deg(body_pitch_deg),
                "time_ms": 0.0,
                "preimpact_qdot_dps": 0.0,
                "energy_drop_mj": 0.0,
            }

        direction = 1.0 if q_target_deg > q_touch_deg else -1.0
        q = radians(q_touch_deg)
        target = radians(q_target_deg)
        v = 0.0
        t = 0.0
        hdeg = 1e-3

        def deriv(qrad: float, qdot: float) -> tuple[float, float]:
            qdeg = degrees(qrad)
            m = self.effective_inertia_kgm2(qdeg, q_touch_deg, body_pitch_deg, q_old_deg)
            mp = (
                self.effective_inertia_kgm2(qdeg+hdeg, q_touch_deg, body_pitch_deg, q_old_deg)
                - self.effective_inertia_kgm2(qdeg-hdeg, q_touch_deg, body_pitch_deg, q_old_deg)
            ) / (2.0 * radians(hdeg))
            up = (
                self.potential_j(qdeg+hdeg, q_touch_deg, body_pitch_deg, q_old_deg)
                - self.potential_j(qdeg-hdeg, q_touch_deg, body_pitch_deg, q_old_deg)
            ) / (2.0 * radians(hdeg))
            return qdot, -(0.5*mp*qdot*qdot + up) / m

        while direction * (q - target) < 0.0 and t < max_s:
            k1 = deriv(q, v)
            k2 = deriv(q + dt_s*k1[0]/2, v + dt_s*k1[1]/2)
            k3 = deriv(q + dt_s*k2[0]/2, v + dt_s*k2[1]/2)
            k4 = deriv(q + dt_s*k3[0], v + dt_s*k3[1])
            q += dt_s * (k1[0] + 2*k2[0] + 2*k3[0] + k4[0]) / 6.0
            v += dt_s * (k1[1] + 2*k2[1] + 2*k3[1] + k4[1]) / 6.0
            t += dt_s

        return {
            "flat_reachable": self.kin.flat_contact_feasible(body_pitch_deg),
            "q_settle_deg": q_target_deg,
            "residual_foot_pitch_deg": self.kin.residual_foot_pitch_at_settle_deg(body_pitch_deg),
            "time_ms": 1000.0*t,
            "preimpact_qdot_dps": degrees(v),
            "energy_drop_mj": self.energy_drop_to_settle_mj(q_touch_deg, body_pitch_deg, q_old_deg),
        }
