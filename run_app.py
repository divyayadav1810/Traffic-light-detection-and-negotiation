"""
Entry point for Traffic Light Detection and Negotiation System
Serves the full-stack simulation, perception HUD, and REST/SSE APIs on localhost.
"""

import sys
import os

# Add backend directory to Python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from server import run_server

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port argument '{sys.argv[1]}', defaulting to 8000")
            port = 8000
    
    url = f"http://localhost:{port}"
    print(f"\n==================================================================")
    print(f"  🚦 TRAFFIC LIGHT DETECTION & NEGOTIATION SYSTEM")
    print(f"  Autonomous Vehicle Intersection Simulation & Perception HUD")
    print(f"==================================================================")
    print(f"  Frontend Dashboard:     {url}")
    print(f"  Telemetry API:          {url}/api/status")
    print(f"  Metrics Benchmark:      {url}/api/metrics")
    print(f"  SSE Stream:             {url}/api/stream")
    print(f"  Press Ctrl+C to terminate.")
    print(f"==================================================================\n")

    run_server(port)
