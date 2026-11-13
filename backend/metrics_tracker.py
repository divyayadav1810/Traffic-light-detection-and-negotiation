"""
Quantitative Analysis & Metrics Tracker
Records telemetry, decision safety, stopping line error, perception accuracy,
and kinematic comfort metrics across simulation runs.
"""

from typing import Dict, Any, List


class MetricsTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_frames = 0
        self.perception_evaluations = 0
        self.correct_perceptions = 0
        self.stopping_events = []
        self.dilemma_decisions = []
        self.max_deceleration_recorded = 0.0
        self.collision_count = 0
        self.telemetry_history: List[Dict[str, float]] = []

    def record_perception(self, predicted_state: str, true_state: str, confidence: float, occlusion: float):
        self.total_frames += 1
        if predicted_state != "UNKNOWN":
            self.perception_evaluations += 1
            if predicted_state == true_state:
                self.correct_perceptions += 1

    def record_kinematics(self, t: float, ego_pos: float, velocity: float, accel: float, distance_to_stop: float):
        if abs(accel) > self.max_deceleration_recorded:
            self.max_deceleration_recorded = round(abs(accel), 2)
            
        # Sample telemetry history (keep latest 150 points for chart rendering)
        if len(self.telemetry_history) >= 150:
            self.telemetry_history.pop(0)
            
        self.telemetry_history.append({
            "t": round(t, 2),
            "pos": round(ego_pos, 1),
            "speed": round(velocity * 3.6, 1),  # in km/h
            "accel": round(accel, 2),
            "dist_to_stop": round(distance_to_stop, 1)
        })

    def record_stopping_event(self, actual_dist_from_stop_line: float, target_stop_buffer: float = 2.5):
        error = round(actual_dist_from_stop_line - target_stop_buffer, 2)
        self.stopping_events.append({
            "actual_distance": round(actual_dist_from_stop_line, 2),
            "target": target_stop_buffer,
            "error_margin": error,
            "successful_stop": abs(error) <= 1.5 and actual_dist_from_stop_line >= 0.0
        })

    def record_dilemma_decision(self, speed: float, dist_to_line: float, decision: str, safe: bool):
        self.dilemma_decisions.append({
            "speed_kmh": round(speed * 3.6, 1),
            "distance_m": round(dist_to_line, 1),
            "decision": decision,
            "safe": safe
        })

    def get_summary(self) -> Dict[str, Any]:
        acc_rate = 0.0
        if self.perception_evaluations > 0:
            acc_rate = round((self.correct_perceptions / self.perception_evaluations) * 100.0, 1)
            
        mean_stop_err = 0.0
        successful_stops = 0
        if len(self.stopping_events) > 0:
            mean_stop_err = round(sum(abs(e["error_margin"]) for e in self.stopping_events) / len(self.stopping_events), 2)
            successful_stops = sum(1 for e in self.stopping_events if e["successful_stop"])

        return {
            "total_frames": self.total_frames,
            "perception_accuracy_percent": acc_rate,
            "correct_detections": self.correct_perceptions,
            "total_evaluations": self.perception_evaluations,
            "mean_stop_error_meters": mean_stop_err,
            "total_stops": len(self.stopping_events),
            "successful_stops": successful_stops,
            "max_deceleration_mps2": self.max_deceleration_recorded,
            "comfort_compliance": self.max_deceleration_recorded <= 3.5,
            "collisions": self.collision_count,
            "dilemma_evaluations": len(self.dilemma_decisions),
            "telemetry_history": self.telemetry_history[-40:]  # Latest points for UI graphs
        }

