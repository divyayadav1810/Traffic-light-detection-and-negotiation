"""
Unit tests for the Traffic Light Negotiation State Machine and Vehicle Dynamics
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from perception_engine import PerceptionEngine
from traffic_controller import TrafficLightController
from state_machine import TrafficLightNegotiator
from metrics_tracker import MetricsTracker


class TestTrafficLightNegotiator(unittest.TestCase):
    def setUp(self):
        self.negotiator = TrafficLightNegotiator(stop_line_pos=100.0, target_speed_kmh=40.0)
        self.perception = PerceptionEngine()
        self.traffic_light = TrafficLightController()
        self.metrics = MetricsTracker()

    def test_initial_cruise(self):
        state = self.negotiator.step(0.1, self.perception, self.traffic_light, self.metrics)
        self.assertEqual(state["state"], "CRUISE")
        self.assertAlmostEqual(state["ego"]["speed_kmh"], 40.0, delta=1.0)
        self.assertAlmostEqual(state["ego"]["position"], 1.11, delta=0.2)

    def test_deceleration_on_red(self):
        # Force traffic signal to RED
        self.traffic_light.set_state("RED")
        # Place ego vehicle closer to stop line (e.g. at 50m)
        self.negotiator.ego_pos = 50.0
        self.negotiator.ego_velocity = 40.0 / 3.6

        state = self.negotiator.step(0.1, self.perception, self.traffic_light, self.metrics)
        self.assertEqual(state["state"], "DECELERATE")
        self.assertLess(state["ego"]["acceleration"], 0.0)

    def test_full_stop_at_stop_line(self):
        self.traffic_light.set_state("RED")
        # Ego stopped just before the stop buffer (97.5m, where line is 100m)
        self.negotiator.ego_pos = 97.4
        self.negotiator.ego_velocity = 0.05
        
        state = self.negotiator.step(0.1, self.perception, self.traffic_light, self.metrics)
        self.assertEqual(state["state"], "STOPPED")
        self.assertAlmostEqual(state["ego"]["speed_kmh"], 0.0, delta=0.1)

    def test_dilemma_zone_behavior(self):
        self.traffic_light.set_state("YELLOW")
        # 1. When far enough, vehicle safely stops
        self.negotiator.ego_pos = 40.0
        self.negotiator.ego_velocity = 40.0 / 3.6
        state1 = self.negotiator.step(0.1, self.perception, self.traffic_light, self.metrics)
        self.assertEqual(state1["state"], "DECELERATE")

        # 2. When too close to stop comfortably (e.g. at 92m, only 8m to line at 40 km/h)
        self.negotiator.ego_pos = 92.0
        self.negotiator.ego_velocity = 40.0 / 3.6
        state2 = self.negotiator.step(0.1, self.perception, self.traffic_light, self.metrics)
        self.assertIn(state2["state"], ["PROCEED", "CREEP"])

    def test_lead_vehicle_queue_stopping(self):
        self.traffic_light.set_state("RED")
        self.negotiator.lead_car_enabled = True
        self.negotiator.lead_car_pos = 60.0
        self.negotiator.lead_car_velocity = 0.0
        self.negotiator.ego_pos = 48.0
        self.negotiator.ego_velocity = 20.0 / 3.6

        state = self.negotiator.step(0.1, self.perception, self.traffic_light, self.metrics)
        self.assertIn(state["state"], ["DECELERATE", "STOPPED"])


if __name__ == "__main__":
    unittest.main()
