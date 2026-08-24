import unittest

from model.leg_kinematics import LegGeometry


class LegKinematicsTest(unittest.TestCase):
    def setUp(self):
        self.g = LegGeometry()

    def test_fixed_geometry_lengths(self):
        self.assertAlmostEqual(self.g.hip_to_fixed_bend_mm, 51.0, places=9)
        self.assertAlmostEqual(self.g.fixed_bend_to_ankle_mm, 47.08161431597531, places=9)
        self.assertAlmostEqual(self.g.hip_to_ankle_radius_mm, 60.19616314992073, places=9)

    def test_cad_pose_and_stop_angle_range(self):
        self.assertAlmostEqual(
            self.g.cad_pose_angle_from_down_vertical_deg,
            10.749373402546517,
            places=9,
        )
        lo, hi = self.g.angle_range_from_down_vertical_deg
        self.assertAlmostEqual(lo, -9.250626597453483, places=9)
        self.assertAlmostEqual(hi, 10.749373402546517, places=9)

    def test_ankle_travel_over_20_degree_stop_range(self):
        self.assertAlmostEqual(self.g.ankle_y_travel_mm, 20.904119998624886, places=9)
        self.assertAlmostEqual(self.g.ankle_travel_from_qmax_mm(-10.0), 10.440099, places=6)
        self.assertAlmostEqual(self.g.stride_fraction_from_qmax(-10.0), 0.49942783, places=7)

    def test_invert_requested_ankle_travel(self):
        q = self.g.q_for_ankle_travel_mm(10.0)
        self.assertAlmostEqual(q, -9.581045989013663, places=9)
        self.assertAlmostEqual(self.g.ankle_travel_from_qmax_mm(q), 10.0, places=9)

    def test_hard_stop_membership(self):
        self.assertTrue(self.g.within_hard_stops(-20.0))
        self.assertTrue(self.g.within_hard_stops(-10.0))
        self.assertTrue(self.g.within_hard_stops(0.0))
        self.assertFalse(self.g.within_hard_stops(-20.1))
        self.assertFalse(self.g.within_hard_stops(+0.1))


if __name__ == "__main__":
    unittest.main()
