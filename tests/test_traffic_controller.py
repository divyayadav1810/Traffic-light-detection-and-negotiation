"""
Unit tests for the Traffic Light Controller
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from traffic_controller import TrafficLightController


class TestTrafficLightController(unittest.TestCase):
    def setUp(self):
        # Durations: Green 5s, Yellow 2s, Red 5s
        self.controller = TrafficLightController(green_duration=5.0, yellow_duration=2.0, red_duration=5.0)

    def test_initial_state(self):
        self.assertEqual(self.controller.current_state, "GREEN")
        self.assertEqual(self.controller.mode, "AUTO")
        self.assertAlmostEqual(self.controller.get_time_remaining(), 5.0, delta=0.1)

    def test_cycle_transitions(self):
        # Step through 5.1s -> should transition from GREEN to YELLOW
        state = self.controller.step(5.1)
        self.assertEqual(state, "YELLOW")
        self.assertEqual(self.controller.current_state, "YELLOW")

        # Step through 2.1s -> should transition from YELLOW to RED
        state = self.controller.step(2.1)
        self.assertEqual(state, "RED")

        # Step through 5.1s -> should transition back to GREEN
        state = self.controller.step(5.1)
        self.assertEqual(state, "GREEN")

    def test_manual_override(self):
        self.controller.set_state("RED")
        self.assertEqual(self.controller.current_state, "RED")
        self.assertEqual(self.controller.mode, "MANUAL")
        
        # In manual mode, stepping time should not cycle states
        state = self.controller.step(10.0)
        self.assertEqual(state, "RED")


if __name__ == "__main__":
    unittest.main()
