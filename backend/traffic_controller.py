"""
Traffic Light Phase Controller
Manages 4-phase cycle (Green -> Yellow -> Red -> Green) with realistic phase timers,
countdown clocks, and manual override modes.
"""

from typing import Dict, Any


class TrafficLightController:
    def __init__(self, green_duration: float = 12.0, yellow_duration: float = 3.5, red_duration: float = 10.0):
        self.green_duration = green_duration
        self.yellow_duration = yellow_duration
        self.red_duration = red_duration
        
        self.mode = "AUTO"  # "AUTO" or "MANUAL"
        self.current_state = "GREEN"  # "GREEN", "YELLOW", "RED"
        self.time_in_state = 0.0
        self.manual_state = "GREEN"

    def set_mode(self, mode: str, force_state: str = "RED"):
        self.mode = mode.upper()
        if self.mode == "MANUAL":
            self.manual_state = force_state.upper()
            self.current_state = self.manual_state
            self.time_in_state = 0.0

    def set_state(self, state: str):
        self.mode = "MANUAL"
        self.manual_state = state.upper()
        self.current_state = self.manual_state
        self.time_in_state = 0.0

    def step(self, dt: float) -> str:
        """Advance traffic light state by dt seconds."""
        if self.mode == "MANUAL":
            self.current_state = self.manual_state
            self.time_in_state += dt
            return self.current_state

        self.time_in_state += dt

        if self.current_state == "GREEN":
            if self.time_in_state >= self.green_duration:
                self.current_state = "YELLOW"
                self.time_in_state = 0.0
        elif self.current_state == "YELLOW":
            if self.time_in_state >= self.yellow_duration:
                self.current_state = "RED"
                self.time_in_state = 0.0
        elif self.current_state == "RED":
            if self.time_in_state >= self.red_duration:
                self.current_state = "GREEN"
                self.time_in_state = 0.0

        return self.current_state

    def get_time_remaining(self) -> float:
        if self.mode == "MANUAL":
            return 99.0
        if self.current_state == "GREEN":
            return max(0.0, self.green_duration - self.time_in_state)
        elif self.current_state == "YELLOW":
            return max(0.0, self.yellow_duration - self.time_in_state)
        elif self.current_state == "RED":
            return max(0.0, self.red_duration - self.time_in_state)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.current_state,
            "mode": self.mode,
            "time_in_state": round(self.time_in_state, 1),
            "time_remaining": round(self.get_time_remaining(), 1),
            "durations": {
                "green": self.green_duration,
                "yellow": self.yellow_duration,
                "red": self.red_duration
            }
        }

