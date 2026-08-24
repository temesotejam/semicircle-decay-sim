import math
import unittest

from model.passive_swing import simulate_until_stop, uniform_step_proxy


class PassiveSwingTest(unittest.TestCase):
    def setUp(self):
        self.p = uniform_step_proxy()

    def test_uniform_step_proxy_geometry(self):
        self.assertAlmostEqual(self.p.cg_angle_from_down_vertical_deg, 32.74730698324174, places=9)
        self.assertAlmostEqual(self.p.inertia_per_mass_about_hip_mm2, 2532.0140795711786, places=9)

    def test_gravity_drives_toward_qmin_at_zero_pitch(self):
        self.assertLess(self.p.gravity_qdd_rad_s2(math.radians(0.0)), 0.0)
        self.assertLess(self.p.gravity_qdd_rad_s2(math.radians(-20.0)), 0.0)
        self.assertLess(
            self.p.potential_per_mass_j_per_kg(math.radians(-20.0)),
            self.p.potential_per_mass_j_per_kg(math.radians(0.0)),
        )

    def test_pitch_screening_boundaries(self):
        self.assertAlmostEqual(
            self.p.pitch_for_zero_gravity_torque_at_qmin_deg,
            -12.74730698324174,
            places=9,
        )
        self.assertAlmostEqual(
            self.p.pitch_energy_reachability_limit_deg,
            -22.74730698324174,
            places=9,
        )

    def test_frictionless_proxy_reaches_stop(self):
        rows, impact = simulate_until_stop(self.p, dt_s=1e-5)
        self.assertIsNotNone(impact)
        impact_t, impact_qdot = impact
        self.assertAlmostEqual(impact_t, 0.09569775169815246, places=6)
        self.assertAlmostEqual(impact_qdot, -371.6745025669435, places=3)
        self.assertEqual(rows[-1][1], -20.0)


if __name__ == "__main__":
    unittest.main()
