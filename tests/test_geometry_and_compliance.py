import math
import unittest

from model.compliant_contact import QuasiStaticCompliantContact
from model.foot_compliance import FootArcSection
from model.rocker_geometry import RockerGeometry


class GeometryComplianceTests(unittest.TestCase):
    def test_step_thickness_and_free_span(self):
        sec = FootArcSection()
        self.assertAlmostEqual(sec.radial_thickness_m, 0.0015, places=12)
        self.assertAlmostEqual(sec.free_span_arc_m, 0.032384942390949835, places=12)

    def test_rigid_inner_angle(self):
        g = RockerGeometry()
        self.assertAlmostEqual(
            math.degrees(g.theta_inner_rad), 1.9102131717099302, places=9
        )

    def test_symmetric_load_sharing(self):
        c = QuasiStaticCompliantContact(
            left_stiffness_n_per_m=3000.0,
            right_stiffness_n_per_m=3000.0,
        )
        s = c.solve(0.0, 2.0)
        self.assertEqual(s.mode, "dual_inner_edges")
        self.assertAlmostEqual(s.left_force_n, 1.0)
        self.assertAlmostEqual(s.right_force_n, 1.0)

    def test_high_foot_unloads(self):
        c = QuasiStaticCompliantContact(
            left_stiffness_n_per_m=3000.0,
            right_stiffness_n_per_m=3000.0,
        )
        s = c.solve(math.radians(10.0), 2.0)
        self.assertEqual(s.mode, "right_only")
        self.assertAlmostEqual(s.left_force_n, 0.0)
        self.assertAlmostEqual(s.right_force_n, 2.0)

    def test_zero_potential_correction(self):
        c = QuasiStaticCompliantContact(
            left_stiffness_n_per_m=3000.0,
            right_stiffness_n_per_m=3000.0,
        )
        self.assertAlmostEqual(
            c.compliance_potential_correction_j(0.0, 0.1997), 0.0, places=15
        )


if __name__ == "__main__":
    unittest.main()
