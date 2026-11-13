"""
Full-Stack Simulation Server
Provides REST APIs, Server-Sent Events (SSE) telemetry stream,
background simulation loop, and serves frontend static web assets.
"""

import os
import sys
import json
import time
import threading
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn


# Ensure backend directory is in python search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from perception_engine import PerceptionEngine
from traffic_controller import TrafficLightController
from state_machine import TrafficLightNegotiator
from metrics_tracker import MetricsTracker


# Global Simulation Context
class SimulationContext:
    def __init__(self):
        self.perception = PerceptionEngine()
        self.traffic_light = TrafficLightController()
        self.negotiator = TrafficLightNegotiator()
        self.metrics = MetricsTracker()
        
        self.is_running = True
        self.sim_speed = 1.0  # Time multiplier
        self.fps = 30.0
        self.lock = threading.Lock()
        
        # SSE subscribers
        self.listeners = []
        self.last_state = {}

    def reset(self, target_speed_kmh: float = 40.0):
        with self.lock:
            self.negotiator.reset(target_speed_kmh=target_speed_kmh)
            self.metrics.reset()
            self.traffic_light.set_mode("AUTO")

    def load_scenario(self, scenario_name: str):
        with self.lock:
            self.negotiator.reset()
            self.metrics.reset()
            
            if scenario_name == "baseline":
                self.perception.set_environment(weather="clear", occlusion_percent=0.0, tree_obstruction=False)
                self.negotiator.lead_car_enabled = False
                self.traffic_light.set_mode("AUTO")
                self.traffic_light.current_state = "RED"
                self.traffic_light.time_in_state = 0.0

            elif scenario_name == "tree_occlusion":
                # Scenario requirement 2a: Traffic lights obstructed by trees
                self.perception.set_environment(weather="clear", occlusion_percent=0.75, tree_obstruction=True)
                self.negotiator.lead_car_enabled = False
                self.traffic_light.set_mode("AUTO")
                self.traffic_light.current_state = "RED"
                self.traffic_light.time_in_state = 2.0

            elif scenario_name == "dilemma_zone":
                # Scenario requirement: Yellow dilemma zone negotiation
                self.perception.set_environment(weather="clear", occlusion_percent=0.0, tree_obstruction=False)
                self.negotiator.lead_car_enabled = False
                self.traffic_light.set_mode("MANUAL", force_state="YELLOW")

            elif scenario_name == "lead_vehicle":
                # Scenario requirement: Ego reacting to lead vehicle on red
                self.perception.set_environment(weather="clear", occlusion_percent=0.0, tree_obstruction=False)
                self.negotiator.lead_car_enabled = True
                self.negotiator.lead_car_pos = 45.0
                self.negotiator.lead_car_velocity = 8.5
                self.traffic_light.set_mode("AUTO")
                self.traffic_light.current_state = "RED"
                self.traffic_light.time_in_state = 0.0

            elif scenario_name == "dense_fog":
                # Scenario requirement 2c: Adverse weather conditions
                self.perception.set_environment(weather="fog", occlusion_percent=0.0, tree_obstruction=False)
                self.negotiator.lead_car_enabled = False
                self.traffic_light.set_mode("AUTO")

            elif scenario_name == "night_glare":
                # Scenario requirement 2c: Night with glare bloom
                self.perception.set_environment(weather="night", occlusion_percent=0.0, tree_obstruction=False)
                self.negotiator.lead_car_enabled = False
                self.traffic_light.set_mode("AUTO")

    def step(self, dt: float) -> dict:
        with self.lock:
            # Step traffic signal
            self.traffic_light.step(dt)
            # Step vehicle negotiation & perception
            state = self.negotiator.step(dt, self.perception, self.traffic_light, self.metrics)
            # Add summary metrics
            state["metrics_summary"] = self.metrics.get_summary()
            self.last_state = state
            return state


sim_context = SimulationContext()


def simulation_worker():
    """Background high-frequency physics/perception loop"""
    dt = 1.0 / sim_context.fps
    while True:
        if sim_context.is_running:
            state = sim_context.step(dt * sim_context.sim_speed)
            # Notify active SSE subscribers
            dead_listeners = []
            for q in list(sim_context.listeners):
                try:
                    q.put_nowait(json.dumps(state))
                except Exception:
                    dead_listeners.append(q)
            for d in dead_listeners:
                if d in sim_context.listeners:
                    sim_context.listeners.remove(d)
        time.sleep(dt)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class SimulationRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve frontend files from ../frontend
        frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
        super().__init__(*args, directory=frontend_dir, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with sim_context.lock:
                data = sim_context.last_state if sim_context.last_state else sim_context.step(0.01)
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif parsed.path == "/api/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with sim_context.lock:
                summary = sim_context.metrics.get_summary()
            self.wfile.write(json.dumps(summary).encode("utf-8"))

        elif parsed.path == "/api/stream":
            # Server-Sent Events (SSE) for real-time 30 FPS updates
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            import queue
            q = queue.Queue(maxsize=10)
            sim_context.listeners.append(q)
            try:
                while True:
                    try:
                        msg = q.get(timeout=1.0)
                        self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        # Heartbeat comment to keep socket open
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                if q in sim_context.listeners:
                    sim_context.listeners.remove(q)

        else:
            # Serve static files (HTML, CSS, JS)
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        body = {}
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            pass

        if parsed.path == "/api/reset":
            speed = float(body.get("speed_kmh", 40.0))
            sim_context.reset(target_speed_kmh=speed)
            self._send_json({"status": "reset", "target_speed": speed})

        elif parsed.path == "/api/play":
            running = body.get("running", not sim_context.is_running)
            sim_context.is_running = running
            self._send_json({"status": "ok", "running": sim_context.is_running})

        elif parsed.path == "/api/step":
            state = sim_context.step(1.0 / sim_context.fps)
            self._send_json(state)

        elif parsed.path == "/api/scenario":
            scenario = body.get("scenario", "baseline")
            sim_context.load_scenario(scenario)
            self._send_json({"status": "scenario_loaded", "scenario": scenario})

        elif parsed.path == "/api/control":
            with sim_context.lock:
                if "speed_kmh" in body:
                    spd = float(body["speed_kmh"])
                    sim_context.negotiator.target_speed = spd / 3.6
                if "weather" in body:
                    sim_context.perception.weather = str(body["weather"]).lower()
                if "occlusion" in body:
                    occ = float(body["occlusion"])
                    sim_context.perception.occlusion_percent = occ
                    sim_context.perception.tree_obstruction_enabled = (occ > 0.05)
                if "lead_vehicle" in body:
                    sim_context.negotiator.lead_car_enabled = bool(body["lead_vehicle"])
                if "light_state" in body:
                    state = str(body["light_state"]).upper()
                    if state in ["RED", "YELLOW", "GREEN"]:
                        sim_context.traffic_light.set_state(state)
                    elif state == "AUTO":
                        sim_context.traffic_light.set_mode("AUTO")
            self._send_json({"status": "updated"})

        else:
            self.send_error(404, "Endpoint Not Found")

    def _send_json(self, data: dict):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        # Silence routine HTTP polling logs for clean output
        pass


def run_server(port: int = 8000):
    # Start physics/perception worker
    worker = threading.Thread(target=simulation_worker, daemon=True)
    worker.start()

    server = ThreadedHTTPServer(("0.0.0.0", port), SimulationRequestHandler)
    print(f"============================================================")
    print(f" Traffic Light Negotiation & Perception Detection System")
    print(f" MathWorks Challenge Hub Project 223 - Localhost Runtime")
    print(f" Server running at: http://localhost:{port}")
    print(f"============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)

