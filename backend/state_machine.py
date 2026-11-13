"""
Traffic Light Negotiation State Machine and Vehicle Dynamics Controller
Models autonomous vehicle decision logic (FSM), kinematic motion, dilemma zone resolution,
and lead vehicle queue negotiation.
"""

import math
import sys
import os
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from perception_engine import PerceptionEngine
from traffic_controller import TrafficLightController
from metrics_tracker import MetricsTracker


class TrafficLightNegotiator:
    def __init__(self, stop_line_pos: float = 100.0, target_speed_kmh: float = 40.0):
        self.stop_line_pos = stop_line_pos  # Intersection stop line at 100 meters
        self.traffic_light_pos = stop_line_pos + 12.0  # Light pole is 12m past stop line
        self.target_speed = target_speed_kmh / 3.6  # Convert km/h to m/s (~11.11 m/s)
        
        # Vehicle Kinematics
        self.ego_pos = 0.0  # meters along road (starts at 0m)
        self.ego_velocity = self.target_speed  # m/s
        self.ego_acceleration = 0.0  # m/s^2
        self.sim_time = 0.0
        
        # Constraints & Parameters
        self.max_accel = 2.2  # m/s^2
        self.comfortable_decel = -2.6  # m/s^2
        self.emergency_decel = -5.0  # m/s^2
        self.stop_buffer = 2.5  # meters before stop line to come to complete rest
        self.lead_vehicle_buffer = 4.5  # meters safety distance behind lead car
        self.reaction_time = 0.35  # seconds
        
        # Lead vehicle (surrounding traffic participant)
        self.lead_car_enabled = False
        self.lead_car_pos = 50.0  # meters
        self.lead_car_velocity = 8.0  # m/s
        self.lead_car_accel = 0.0
        
        # Stateflow Finite State Machine
        # States: "CRUISE", "DECELERATE", "STOPPED", "WAITING", "PROCEED", "CREEP", "EMERGENCY_BRAKE"
        self.current_fsm_state = "CRUISE"
        self.fsm_reason = "Cruising at target velocity towards intersection."
        self.dilemma_zone_active = False
        self.passed_intersection = False

    def reset(self, target_speed_kmh: float = 40.0):
        self.target_speed = target_speed_kmh / 3.6
        self.ego_pos = 0.0
        self.ego_velocity = self.target_speed
        self.ego_acceleration = 0.0
        self.sim_time = 0.0
        self.current_fsm_state = "CRUISE"
        self.fsm_reason = "Cruising at target velocity towards intersection."
        self.dilemma_zone_active = False
        self.passed_intersection = False
        
        if self.lead_car_enabled:
            self.lead_car_pos = 45.0
            self.lead_car_velocity = self.target_speed * 0.85
            self.lead_car_accel = 0.0

    def step(
        self,
        dt: float,
        perception: PerceptionEngine,
        traffic_light: TrafficLightController,
        metrics: MetricsTracker
    ) -> Dict[str, Any]:
        """
        Execute one control cycle (typically 30-60 Hz).
        Performs perception, state evaluation, kinematic integration, and metrics logging.
        """
        self.sim_time += dt

        # 1. Update Lead Vehicle Kinematics (if enabled)
        self._update_lead_vehicle(dt, traffic_light.current_state)

        # 2. Run Perception Pipeline
        lead_pos_arg = self.lead_car_pos if self.lead_car_enabled else None
        sensor_data = perception.process_frame(
            ego_pos=self.ego_pos,
            light_pos=self.traffic_light_pos,
            true_light_state=traffic_light.current_state,
            lead_car_pos=lead_pos_arg
        )

        fused_light_state = sensor_data["fused"]["state"]
        fused_light_conf = sensor_data["fused"]["confidence"]
        dist_to_light = sensor_data["fused"]["distance"]

        # Log perception evaluation
        metrics.record_perception(
            fused_light_state,
            traffic_light.current_state,
            fused_light_conf,
            perception.occlusion_percent
        )

        # 3. Geometry & Distances
        dist_to_stop_line = self.stop_line_pos - self.ego_pos
        has_crossed_stop_line = dist_to_stop_line <= 0.0

        if has_crossed_stop_line and not self.passed_intersection:
            self.passed_intersection = True

        # Calculate required stopping distance at current velocity
        v = max(0.0, self.ego_velocity)
        if abs(self.comfortable_decel) > 0.01:
            req_stopping_dist = (v * v) / (2.0 * abs(self.comfortable_decel)) + (v * self.reaction_time)
        else:
            req_stopping_dist = 0.0

        # Check Lead Vehicle Constraint
        dist_to_lead = None
        lead_speed = 0.0
        must_stop_for_lead = False
        if self.lead_car_enabled and self.lead_car_pos > self.ego_pos:
            dist_to_lead = self.lead_car_pos - self.ego_pos
            lead_speed = self.lead_car_velocity
            if dist_to_lead < (self.lead_vehicle_buffer + 15.0) and lead_speed < v:
                must_stop_for_lead = True

        # 4. Stateflow Decision Logic (Traffic Light Negotiation)
        target_accel = 0.0
        self.dilemma_zone_active = False

        if self.passed_intersection:
            # Vehicle successfully cleared intersection
            self.current_fsm_state = "PROCEED"
            self.fsm_reason = "Intersection cleared. Accelerating to highway cruising speed."
            target_accel = self._calculate_accel_to_target(self.target_speed)

        elif must_stop_for_lead:
            # Lead Vehicle Queue Handling (Adaptive Cruise Control Stop)
            target_distance = self.lead_vehicle_buffer
            effective_gap = dist_to_lead - target_distance
            
            if effective_gap <= 0.5:
                self.current_fsm_state = "STOPPED"
                self.fsm_reason = f"Stopped safely in traffic queue behind lead vehicle ({round(dist_to_lead, 1)}m gap)."
                target_accel = self.emergency_decel if v > 1.0 else 0.0
            else:
                self.current_fsm_state = "DECELERATE"
                self.fsm_reason = f"Decelerating for leading vehicle ahead ({round(dist_to_lead, 1)}m away)."
                target_accel = self._calculate_stopping_accel(effective_gap)

        else:
            # Signal-Based Negotiation
            if fused_light_state == "RED":
                effective_dist_to_stop = dist_to_stop_line - self.stop_buffer
                
                if effective_dist_to_stop <= 0.2 and v < 0.2:
                    self.current_fsm_state = "STOPPED"
                    self.fsm_reason = f"Holding at stop line. Distance to line: {round(dist_to_stop_line, 1)}m. Waiting for Green."
                    target_accel = 0.0
                    if len(metrics.stopping_events) == 0 or not metrics.stopping_events[-1]["successful_stop"]:
                        metrics.record_stopping_event(dist_to_stop_line, self.stop_buffer)
                elif effective_dist_to_stop <= 0.2:
                    self.current_fsm_state = "STOPPED"
                    self.fsm_reason = "Final braking hold at intersection line."
                    target_accel = self.comfortable_decel
                else:
                    self.current_fsm_state = "DECELERATE"
                    self.fsm_reason = f"Perception identified RED light ({round(dist_to_stop_line, 1)}m). Applying smooth deceleration."
                    target_accel = self._calculate_stopping_accel(effective_dist_to_stop)

            elif fused_light_state == "YELLOW":
                # Dilemma Zone Logic
                effective_dist_to_stop = dist_to_stop_line - self.stop_buffer
                self.dilemma_zone_active = True
                
                # Can we stop comfortably before line?
                if effective_dist_to_stop >= req_stopping_dist:
                    # Yes, safe to stop
                    self.current_fsm_state = "DECELERATE"
                    self.fsm_reason = f"YELLOW light detected with sufficient stopping margin ({round(effective_dist_to_stop, 1)}m > {round(req_stopping_dist, 1)}m). Decelerating to stop."
                    target_accel = self._calculate_stopping_accel(effective_dist_to_stop)
                    metrics.record_dilemma_decision(v, dist_to_stop_line, "STOP", True)
                else:
                    # Inside dilemma zone: cannot stop comfortably without harsh braking
                    self.current_fsm_state = "CREEP" if v < 4.0 else "PROCEED"
                    self.fsm_reason = f"Inside dilemma zone ({round(dist_to_stop_line, 1)}m to line). Insufficient distance to brake comfortably. Safely clearing intersection."
                    target_accel = self._calculate_accel_to_target(self.target_speed)
                    metrics.record_dilemma_decision(v, dist_to_stop_line, "CLEAR", True)

            elif fused_light_state == "GREEN":
                if self.current_fsm_state in ["STOPPED", "WAITING"]:
                    self.current_fsm_state = "PROCEED"
                    self.fsm_reason = "Perception identified GREEN signal. Transitioning to acceleration."
                else:
                    self.current_fsm_state = "CRUISE"
                    self.fsm_reason = f"GREEN light detected ({round(fused_light_conf*100, 1)}% conf). Cruising smoothly through intersection."
                
                target_accel = self._calculate_accel_to_target(self.target_speed)

            else:
                # UNKNOWN state (e.g. heavy occlusion, camera blinded)
                if dist_to_stop_line < 35.0 and not has_crossed_stop_line:
                    # Fail-safe defensive driving: gently slow down if signal cannot be confirmed near intersection
                    self.current_fsm_state = "DECELERATE"
                    self.fsm_reason = "Defensive control: Signal unconfirmed near intersection. Pre-braking."
                    target_accel = -1.2
                else:
                    self.current_fsm_state = "CRUISE"
                    self.fsm_reason = "Approaching intersection. Scanning for traffic signals."
                    target_accel = self._calculate_accel_to_target(self.target_speed)

        # 5. Vehicle Kinematic Integration (Euler forward simulation)
        # Apply comfortable limits
        target_accel = max(self.emergency_decel, min(self.max_accel, target_accel))
        
        # Smooth acceleration change (jerk rate limiting)
        jerk_limit = 4.5 * dt
        accel_error = target_accel - self.ego_acceleration
        accel_step = max(-jerk_limit, min(jerk_limit, accel_error))
        self.ego_acceleration += accel_step

        # Update velocity & position
        self.ego_velocity = max(0.0, self.ego_velocity + self.ego_acceleration * dt)
        if self.current_fsm_state == "STOPPED" and self.ego_velocity < 0.1:
            self.ego_velocity = 0.0
            self.ego_acceleration = 0.0
            
        self.ego_pos += self.ego_velocity * dt

        # Log kinematics
        metrics.record_kinematics(
            self.sim_time,
            self.ego_pos,
            self.ego_velocity,
            self.ego_acceleration,
            dist_to_stop_line
        )

        return {
            "time": round(self.sim_time, 2),
            "state": self.current_fsm_state,
            "reason": self.fsm_reason,
            "ego": {
                "position": round(self.ego_pos, 2),
                "speed_kmh": round(self.ego_velocity * 3.6, 1),
                "speed_mps": round(self.ego_velocity, 2),
                "acceleration": round(self.ego_acceleration, 2),
                "target_speed_kmh": round(self.target_speed * 3.6, 1),
                "distance_to_stop_line": round(dist_to_stop_line, 1),
                "required_stopping_dist": round(req_stopping_dist, 1),
                "dilemma_zone": self.dilemma_zone_active,
                "passed_intersection": self.passed_intersection
            },
            "lead_car": {
                "enabled": self.lead_car_enabled,
                "position": round(self.lead_car_pos, 1) if self.lead_car_enabled else None,
                "speed_kmh": round(self.lead_car_velocity * 3.6, 1) if self.lead_car_enabled else None,
                "distance_from_ego": round(dist_to_lead, 1) if dist_to_lead is not None else None
            },
            "perception": sensor_data,
            "traffic_light": traffic_light.to_dict()
        }

    def _calculate_stopping_accel(self, distance_remaining: float) -> float:
        """Computes smooth constant deceleration profile: a = -v^2 / (2 * d)"""
        d = max(0.8, distance_remaining)
        v = self.ego_velocity
        if v < 0.2:
            return 0.0
        req_a = -(v * v) / (2.0 * d)
        return max(self.emergency_decel, min(-0.4, req_a))

    def _calculate_accel_to_target(self, target_vel: float) -> float:
        """P-controller towards target speed"""
        vel_err = target_vel - self.ego_velocity
        kp = 1.2
        return max(self.comfortable_decel, min(self.max_accel, vel_err * kp))

    def _update_lead_vehicle(self, dt: float, light_state: str):
        """Simulates realistic traffic participant in front of ego vehicle"""
        if not self.lead_car_enabled:
            return

        dist_to_stop = self.stop_line_pos - self.lead_car_pos
        
        if dist_to_stop <= 2.0:
            # Lead car is at stop line
            if light_state in ["RED", "YELLOW"]:
                # Stop at line
                self.lead_car_velocity = max(0.0, self.lead_car_velocity - 3.5 * dt)
                self.lead_car_accel = -3.5 if self.lead_car_velocity > 0.0 else 0.0
            else:
                # Green light: accelerate away
                self.lead_car_velocity = min(self.target_speed * 0.9, self.lead_car_velocity + 1.8 * dt)
                self.lead_car_accel = 1.8
        elif dist_to_stop < 30.0 and light_state in ["RED", "YELLOW"]:
            # Decelerate towards stop line
            self.lead_car_velocity = max(0.0, self.lead_car_velocity - 2.2 * dt)
            self.lead_car_accel = -2.2
        else:
            # Cruising
            self.lead_car_velocity = min(self.target_speed * 0.9, self.lead_car_velocity + 0.8 * dt)
            self.lead_car_accel = 0.5

        self.lead_car_pos += self.lead_car_velocity * dt

