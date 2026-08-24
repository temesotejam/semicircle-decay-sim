import unittest

from model.support_transfer import SupportTransferKinematics


class SupportTransferKinematicsTest(unittest.TestCase):
    def setUp(self):
        self.k = SupportTransferKinematics()

    def test_foot_pitch_is_body_plus_leg(self):
        self.assertAlmostEqual(self.k.foot_pitch_deg(-10.0, 3.0), -7.0)

    def test_zero_body_pitch_flattens_at_q_zero(self):
        self.assertAlmostEqual(self.k.flat_target_q_deg(0.0), 0.0)
        self.assertTrue(self.k.flat_contact_feasible(0.0))
        self.assertAlmostEqual(self.k.residual_foot_pitch_at_settle_deg(0.0), 0.0)

    def test_positive_body_pitch_can_be_compensated_inside_stops(self):
        self.assertAlmostEqual(self.k.flat_target_q_deg(8.0), -8.0)
        self.assertTrue(self.k.flat_contact_feasible(8.0))
        self.assertAlmostEqual(self.k.residual_foot_pitch_at_settle_deg(8.0), 0.0)

    def test_negative_body_pitch_cannot_be_fully_flattened_with_qmax_zero(self):
        self.assertAlmostEqual(self.k.flat_target_q_deg(-5.0), 5.0)
        self.assertFalse(self.k.flat_contact_feasible(-5.0))
        self.assertAlmostEqual(self.k.nearest_settle_q_deg(-5.0), 0.0)
        self.assertAlmostEqual(self.k.residual_foot_pitch_at_settle_deg(-5.0), -5.0)

    def test_too_large_positive_pitch_hits_qmin(self):
        self.assertFalse(self.k.flat_contact_feasible(25.0))
        self.assertAlmostEqual(self.k.nearest_settle_q_deg(25.0), -20.0)
        self.assertAlmostEqual(self.k.residual_foot_pitch_at_settle_deg(25.0), 5.0)

    def test_settle_progress(self):
        self.assertAlmostEqual(self.k.settle_progress(-10.0, -10.0, 0.0), 0.0)
        self.assertAlmostEqual(self.k.settle_progress(-10.0, -5.0, 0.0), 0.5)
        self.assertAlmostEqual(self.k.settle_progress(-10.0, 0.0, 0.0), 1.0)


if __name__ == "__main__":
    unittest.main()
