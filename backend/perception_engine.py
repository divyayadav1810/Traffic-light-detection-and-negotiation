"""
Perception Engine for Traffic Light Detection and Sensor Fusion
Simulates computer vision processing, bounding box detection, color classification,
weather degradations (fog, rain, night glare), tree branch occlusion, and sensor fusion.
"""

import math
import random
from typing import Dict, Any, Tuple, Optional


class PerceptionEngine:
    def __init__(self):
        # Camera sensor intrinsics (simulated 1080p automotive camera)
        self.camera_fov = 60.0  # degrees horizontal
        self.camera_height = 1.3  # meters above ground
        self.max_detection_range = 120.0  # meters
        
        # Environmental conditions
        self.weather = "clear"  # "clear", "rain", "fog", "night"
        self.occlusion_percent = 0.0  # 0.0 to 1.0 (e.g. tree branch coverage)
        self.tree_obstruction_enabled = False
        
        # Sensor fusion tracking history
        self.tracked_signal_state = "UNKNOWN"
        self.state_confidence_history = []
        self.history_window = 5

    def set_environment(self, weather: str = "clear", occlusion_percent: float = 0.0, tree_obstruction: bool = False):
        self.weather = weather.lower()
        self.occlusion_percent = max(0.0, min(1.0, occlusion_percent))
        self.tree_obstruction_enabled = tree_obstruction

    def process_frame(
        self,
        ego_pos: float,
        light_pos: float,
        true_light_state: str,
        lead_car_pos: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Simulate vision pipeline detecting the traffic light and surrounding participants.
        
        Args:
            ego_pos: Distance along road in meters (0 to 150m)
            light_pos: Position of traffic light (e.g. 100m)
            true_light_state: 'RED', 'YELLOW', 'GREEN'
            lead_car_pos: Position of vehicle in front of ego (if any)
            
        Returns:
            Dictionary with vision detection, radar range, and fused output.
        """
        distance_to_light = light_pos - ego_pos
        
        # 1. Optical Visibility & Camera Geometry
        in_camera_view = 1.0 < distance_to_light <= self.max_detection_range
        
        # Compute bounding box in 1920x1080 image plane
        bbox = None
        if in_camera_view:
            # Perspective projection: height scales inversely with distance
            # Near (10m): bbox height ~ 180px; Far (100m): bbox height ~ 22px
            h = max(18, min(240, int(1800.0 / max(5.0, distance_to_light))))
            w = int(h * 0.36)  # aspect ratio of 3-bulb housing
            
            # Position in windshield camera frame (centered slightly above horizon)
            cx = 960 + int((random.random() - 0.5) * 2)  # slight vehicle vibration
            cy = 400 - int(h * 0.4)
            bbox = {
                "x": cx - w // 2,
                "y": cy - h // 2,
                "w": w,
                "h": h
            }

        # 2. Base Optical Confidence Calculation
        if in_camera_view:
            # Distance attenuation: confidence drops as distance exceeds 70m
            if distance_to_light < 60.0:
                base_confidence = 0.96
            else:
                base_confidence = max(0.40, 0.96 - (distance_to_light - 60.0) * 0.012)
        else:
            base_confidence = 0.0

        # 3. Weather Degradations
        weather_factor = 1.0
        contrast_ratio = 1.0
        glare_intensity = 0.0
        
        if self.weather == "fog":
            # Koschmieder's law attenuation in dense fog (beta = 0.035)
            weather_factor = max(0.35, math.exp(-0.035 * max(0.0, distance_to_light)))
            contrast_ratio = 0.45
        elif self.weather == "rain":
            weather_factor = 0.82
            contrast_ratio = 0.75
        elif self.weather == "night":
            weather_factor = 0.92  # Light stands out well at night, but glare blooms
            glare_intensity = 0.70
            contrast_ratio = 0.90

        # 4. Tree Obstruction / Occlusion Degradation
        effective_occlusion = 0.0
        if self.tree_obstruction_enabled:
            # Tree obstructs primarily when vehicle is between 25m and 65m away from light
            if 25.0 <= distance_to_light <= 65.0:
                effective_occlusion = max(self.occlusion_percent, 0.55)
            else:
                effective_occlusion = self.occlusion_percent * 0.3

        occlusion_factor = max(0.05, 1.0 - effective_occlusion * 0.85)

        # Final Vision Confidence
        vision_confidence = round(base_confidence * weather_factor * occlusion_factor, 3)

        # 5. Vision State Classification (with noise/misclassification when confidence < 0.50)
        detected_state = "UNKNOWN"
        if in_camera_view and vision_confidence > 0.25:
            # If confidence is degraded severely, small chance of UNKNOWN or flicker
            if vision_confidence < 0.40 and random.random() < 0.25:
                detected_state = "UNKNOWN"
            else:
                detected_state = true_light_state

        # Distance estimation from camera (with realistic optical sensor noise ~3%)
        optical_distance_est = None
        if in_camera_view:
            noise = (random.random() - 0.5) * 0.04 * distance_to_light
            optical_distance_est = round(max(0.0, distance_to_light + noise), 2)

        # 6. Radar / V2X Range Sensor (Sensor Fusion Input)
        # Radar is unaffected by weather and tree foliage, but has lower semantic precision
        radar_range = None
        radar_confidence = 0.0
        if distance_to_light > 0.5 and distance_to_light <= 110.0:
            radar_noise = (random.random() - 0.5) * 0.5
            radar_range = round(distance_to_light + radar_noise, 2)
            radar_confidence = 0.95

        # 7. Lead Vehicle Perception (Radar + Camera)
        lead_car_detection = None
        if lead_car_pos is not None and lead_car_pos > ego_pos:
            distance_to_lead = lead_car_pos - ego_pos
            if distance_to_lead <= 80.0:
                lead_car_detection = {
                    "detected": True,
                    "distance": round(distance_to_lead, 2),
                    "relative_velocity": 0.0,
                    "confidence": 0.98 if self.weather == "clear" else 0.88,
                    "ttc": round(distance_to_lead / max(0.1, 10.0), 1)  # approx time to collision
                }

        # 8. Sensor Fusion (Bayesian belief update across frames)
        fused_state = self._fuse_sensor_data(detected_state, vision_confidence, true_light_state)

        return {
            "in_view": in_camera_view,
            "vision": {
                "detected": in_camera_view and vision_confidence > 0.30,
                "state": detected_state,
                "confidence": vision_confidence,
                "bbox": bbox,
                "estimated_distance": optical_distance_est,
                "weather_attenuation": round(weather_factor, 2),
                "occlusion_ratio": round(effective_occlusion, 2),
                "contrast": contrast_ratio,
                "glare": glare_intensity
            },
            "radar": {
                "distance_to_intersection": radar_range,
                "confidence": radar_confidence
            },
            "lead_vehicle": lead_car_detection,
            "fused": {
                "state": fused_state["state"],
                "confidence": fused_state["confidence"],
                "distance": optical_distance_est if optical_distance_est is not None else radar_range,
                "tracking_status": "LOCKED" if fused_state["confidence"] > 0.6 else "ACQUIRING"
            }
        }

    def _fuse_sensor_data(self, vision_state: str, vision_conf: float, true_state: str) -> Dict[str, Any]:
        """
        Maintains temporal tracking memory. If vision briefly drops out due to tree occlusion,
        the tracking filter preserves the previous confirmed state with decaying confidence.
        """
        if vision_state != "UNKNOWN" and vision_conf >= 0.45:
            self.tracked_signal_state = vision_state
            self.state_confidence_history.append(vision_conf)
            if len(self.state_confidence_history) > self.history_window:
                self.state_confidence_history.pop(0)
            avg_conf = sum(self.state_confidence_history) / len(self.state_confidence_history)
            return {"state": vision_state, "confidence": round(avg_conf, 3)}
        else:
            # Memory persistence (sensor fusion tracking through brief occlusion)
            if self.tracked_signal_state != "UNKNOWN" and len(self.state_confidence_history) > 0:
                # Decay confidence by 15% per frame
                decayed_conf = max(0.20, self.state_confidence_history[-1] * 0.85)
                self.state_confidence_history.append(decayed_conf)
                if len(self.state_confidence_history) > self.history_window:
                    self.state_confidence_history.pop(0)
                return {"state": self.tracked_signal_state, "confidence": round(decayed_conf, 3)}
            
            return {"state": "UNKNOWN", "confidence": 0.0}

