"""
Unit tests for the Perception Engine
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from perception_engine import PerceptionEngine


class TestPerceptionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PerceptionEngine()

    def test_detection_in_range(self):
        # Light at 112m, ego at 30m -> distance = 82m
        result = self.engine.process_frame(ego_pos=30.0, light_pos=112.0, true_light_state="GREEN")
        self.assertTrue(result["in_view"])
        self.assertIsNotNone(result["vision"]["bbox"])
        self.assertEqual(result["fused"]["state"], "GREEN")
        self.assertGreater(result["fused"]["confidence"], 0.4)

    def test_out_of_range(self):
        # Distance > 120m
        result = self.engine.process_frame(ego_pos=0.0, light_pos=150.0, true_light_state="RED")
        self.assertFalse(result["in_view"])
        self.assertIsNone(result["vision"]["bbox"])

    def test_fog_attenuation(self):
        self.engine.set_environment(weather="fog")
        result = self.engine.process_frame(ego_pos=20.0, light_pos=112.0, true_light_state="RED")
        self.assertLess(result["vision"]["contrast"], 0.6)
        self.assertLess(result["vision"]["weather_attenuation"], 1.0)

    def test_tree_occlusion_and_fusion(self):
        self.engine.set_environment(weather="clear", occlusion_percent=0.75, tree_obstruction=True)
        # Position ego where tree obstructs (25m to 65m from light)
        # Light at 112m -> ego at 60m -> dist = 52m
        result = self.engine.process_frame(ego_pos=60.0, light_pos=112.0, true_light_state="YELLOW")
        self.assertGreater(result["vision"]["occlusion_ratio"], 0.5)
        # Sensor fusion radar should still report range accurately
        self.assertIsNotNone(result["radar"]["distance_to_intersection"])
        self.assertAlmostEqual(result["radar"]["distance_to_intersection"], 52.0, delta=1.5)

    def test_lead_vehicle_perception(self):
        result = self.engine.process_frame(
            ego_pos=20.0,
            light_pos=112.0,
            true_light_state="RED",
            lead_car_pos=50.0
        )
        self.assertIsNotNone(result["lead_vehicle"])
        self.assertTrue(result["lead_vehicle"]["detected"])
        self.assertAlmostEqual(result["lead_vehicle"]["distance"], 30.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
