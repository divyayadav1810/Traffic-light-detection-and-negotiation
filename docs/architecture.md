# System Architecture & Technical Specifications

This document outlines the architecture, dataflow, and subsystem design of the **Traffic Light Detection and Negotiation System**.

```
                           +-------------------------------------+
                           |      Environment & Weather Engine   |
                           |  (Fog, Rain, Night, Tree Occlusion) |
                           +-------------------------------------+
                                              |
                                              v
+-------------------+      +-------------------------------------+      +---------------------+
| Traffic Signal    | ---> |        Perception Subsystem         | <--- |   Lead Vehicle      |
| Phase Controller  |      | - Vision Pipeline (Color/BBox/Dist) |      |   Tracking Sensor   |
| (Auto 4-Phase/Man)|      | - Sensor Fusion (Optical + Radar)   |      |   (ACC Gap/Speed)   |
+-------------------+      +-------------------------------------+      +---------------------+
                                              |
                                              | Fused Signal State & Distances
                                              v
                           +-------------------------------------+
                           | Stateflow Decision & Control Engine |
                           | - FSM: CRUISE / DECEL / STOP / GO   |
                           | - Dilemma Zone Evaluation           |
                           | - Longitudinal Kinematic Actuator   |
                           +-------------------------------------+
                                              |
                                              | Telemetry (30 Hz)
                                              v
                           +-------------------------------------+
                           | Multi-threaded Server & Stream API  |
                           | - REST Endpoints (/api/status, etc) |
                           | - Server-Sent Events (SSE) Stream   |
                           +-------------------------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |      Cockpit Web Dashboard HUD      |
                           | - 2.5D Animated Intersection Canvas |
                           | - Windshield Camera Perception View |
                           | - Live Telemetry & Metrics Gauges   |
                           +-------------------------------------+
```

---

## 1. Perception Subsystem (`backend/perception_engine.py`)

The perception subsystem models real-world automotive computer vision and sensor fusion pipelines:

### Optical Camera Sensor
- **Resolution & Aspect:** Simulated $1920 \times 1080$ automotive camera sensor with a $60^\circ$ horizontal Field of View (FOV).
- **Perspective Bounding Box:** Bounding box scale $h$ is inversely proportional to range:
  $$h = \text{clamp}\left(18, 240, \frac{1800}{\max(5.0, d)}\right)$$
- **Color Classification:** Identifies lamp chrominance across RED, YELLOW, GREEN, and UNKNOWN.
- **Environmental Degradations:**
  - **Dense Fog:** Modulates contrast and visibility following Koschmieder's attenuation law.
  - **Heavy Rain:** Injects optical noise streaks and causes confidence variance.
  - **Night Driving:** Dark ambient backdrop with heightened lamp glare bloom.
  - **Tree Obstruction:** Simulates roadside foliage occluding the signal head between $25\text{ m}$ and $65\text{ m}$.

### Sensor Fusion & Tracking Memory
- Combines optical camera state with radar range measurements.
- Implements a temporal tracking buffer: when visual line-of-sight is temporarily broken by a tree branch, tracking memory preserves the last confirmed state with decaying confidence, preventing erratic phantom braking.

---

## 2. Stateflow Decision & Control Engine (`backend/state_machine.py`)

The vehicle decision logic operates as a deterministic Finite State Machine (FSM):

| State | Activation Trigger | Kinematic Control Action |
| :--- | :--- | :--- |
| **`CRUISE`** | Approaching intersection with Green signal or clear path | Regulates speed to target velocity ($40\text{ km/h}$) |
| **`DECELERATE`** | Perceived Red signal, queue ahead, or Yellow outside dilemma zone | Smooth deceleration profile ($a = -2.6\text{ m/s}^2$) |
| **`STOPPED`** | Vehicle speed $< 0.1\text{ m/s}$ within stop buffer ($2.5\text{ m}$ to line) | Holds zero velocity; brakes engaged |
| **`WAITING`** | Stopped at line while signal remains Red | Monitors perception stream for Green transition |
| **`PROCEED`** | Green signal detected or intersection successfully cleared | Positive acceleration ($+2.0\text{ m/s}^2$) to target speed |
| **`CREEP`** | Dilemma zone clearance or slow approach | Low-speed transit ($10\text{ km/h}$) |

---

## 3. Communication & Streaming Protocol (`backend/server.py`)

- **REST API:**
  - `GET /api/status`: Snapshot of world state, vehicle position, velocity, and perception outputs.
  - `GET /api/metrics`: Performance analytics (mean stop line deviation, comfort index).
  - `POST /api/play`: Toggle pause / resume simulation.
  - `POST /api/step`: Single-frame kinematic advance.
  - `POST /api/reset`: Reset vehicle to start position.
  - `POST /api/scenario`: Load preset test scenarios.
  - `POST /api/control`: Runtime parameter overrides (speed, weather, occlusion).
- **Server-Sent Events (SSE):**
  - Endpoint: `/api/stream`
  - Broadcasts updates at 30 FPS to all connected web clients without client polling overhead.
