# Traffic Light Detection and Negotiation System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-success.svg)]()
[![Tests: Passing](https://img.shields.io/badge/Tests-13%20Passed-success.svg)]()

An autonomous vehicle intersection management framework combining real-time perception-based traffic light detection, optical degradation modeling, and Stateflow-style decision logic for traffic light negotiation.

---

## 📌 Table of Contents
- [Project Overview](#-project-overview)
- [Problem Statement](#-problem-statement)
- [Objectives](#-objectives)
- [Key Features](#-key-features)
- [Project Architecture](#-project-architecture)
- [Technologies Used](#-technologies-used)
- [Installation Instructions](#-installation-instructions)
- [How to Run the Project](#-how-to-run-the-project)
- [Interactive Scenarios](#-interactive-scenarios)
- [Visual Dashboard Layout](#-visual-dashboard-layout)
- [Mathematical Formulation](#-mathematical-formulation)
- [Testing](#-testing)
- [Future Improvements](#-future-improvements)
- [License](#-license)

---

## 📖 Project Overview

Autonomous intersection crossing is among the most safety-critical challenges in self-driving vehicle systems. An ego vehicle must accurately detect traffic signals across dynamic weather conditions, handle partial occlusions (such as tree branches or roadside structures), arbitrate between lead vehicles, and execute comfortable, deterministic deceleration and acceleration trajectories.

This project delivers a complete, full-stack simulation and evaluation platform featuring:
1. **Perception Engine:** Detects traffic light bounding boxes, classifies signal states (Red, Yellow, Green), estimates distance, and models environmental degradations (fog, rain, night glare, tree occlusion).
2. **Stateflow Negotiation Controller:** Deterministic Finite State Machine (`CRUISE`, `DECELERATE`, `STOPPED`, `WAITING`, `PROCEED`, `CREEP`) governing vehicle kinematics, dilemma zone resolution, and car-following queue handling.
3. **Interactive Localhost Dashboard:** A 2.5D animated roadway intersection and onboard windshield camera HUD streaming real-time telemetry at 30 FPS.

---

## ⚠️ Problem Statement

Navigating signalized intersections with automated driving systems entails several non-trivial engineering hurdles:
- **Perception Ambiguity:** Traffic signals can be partially obscured by roadside vegetation or compromised by low optical contrast in dense fog or high lens glare at night.
- **Dilemma Zones:** A vehicle traveling at speed toward a light that turns yellow must instantaneously arbitrate between stopping safely without harsh deceleration and clearing the intersection before red.
- **Multi-Agent Coordination:** The ego vehicle must halt behind queued lead vehicles rather than attempting to reach the physical stop line if the lane is obstructed.
- **Sensor Fusion:** Relying strictly on computer vision introduces vulnerability during transient dropouts; fusing optical tracking with radar range sensors ensures state persistence.

---

## 🎯 Objectives

- **Develop a Robust Perception Pipeline:** Accurately classify traffic light colors and positions with confidence scoring and optical range calculation.
- **Simulate Real-World Environmental Challenges:** Incorporate atmospheric contrast attenuation (Koschmieder's law for fog), rain noise, headlight/bloom glare, and tree branch occlusions.
- **Implement Stateflow-Style Decision Logic:** Enforce smooth, jerk-limited kinematic transitions that adhere to comfort boundaries ($a_{\text{comf}} \ge -2.6\text{ m/s}^2$).
- **Solve the Dilemma Zone:** Determine whether to brake or proceed based on dynamic stopping distance versus distance remaining to the stop line.
- **Provide Quantitative Evaluation:** Track stop line error margin, classification accuracy, and passenger comfort compliance.

---

## ✨ Key Features

- **2.5D Animated Intersection Canvas:** Dynamic rendering of road lanes, crosswalks, stop lines, traffic light towers with glow halos, trees, and participant vehicles.
- **Onboard Windshield Camera HUD:** First-person driver perspective showing AI bounding boxes, state tags, detection confidence, and synthetic weather effects.
- **Sensor Fusion with Tracking Memory:** Preserves signal state history across intermittent occlusions using Bayesian confidence decay.
- **Six Pre-Configured Test Scenarios:** Single-click execution of baseline approaches, tree obstructions, dilemma zones, lead vehicle queues, and severe weather.
- **Full-Stack REST & SSE Streaming Architecture:** Zero external framework dependencies; built with Python's high-concurrency standard library and modern HTML5/Canvas.
- **Automated Test Suite:** Complete unit test coverage for perception, kinematics, and traffic light phase transitions.

---

## 🏗️ Project Architecture

```
Traffic-light-detection-and-negotiation/
├── backend/                        # Simulation & Control Server
│   ├── perception_engine.py        # Vision detection, occlusion & sensor fusion
│   ├── state_machine.py            # FSM decision logic & vehicle kinematics
│   ├── traffic_controller.py       # 4-phase traffic light controller
│   ├── metrics_tracker.py          # Quantitative analytics & telemetry logger
│   └── server.py                   # Multi-threaded HTTP & SSE streaming server
├── frontend/                       # Interactive Cockpit Web Dashboard
│   ├── index.html                  # Dashboard layout & telemetry views
│   ├── style.css                   # Automotive dark HUD aesthetic
│   └── app.js                      # 2.5D canvas renderer & stream consumer
├── tests/                          # Automated Unit Test Suite
│   ├── test_perception.py          # Vision & sensor fusion validation
│   ├── test_state_machine.py       # FSM transitions & dilemma zone tests
│   └── test_traffic_controller.py  # Phase timing & override tests
├── docs/                           # Technical Specifications
│   ├── architecture.md             # Subsystem dataflow & diagrams
│   └── mathematical_models.md      # Governing equations & formulas
├── run_app.py                      # Root launcher script
├── start.bat                       # Windows one-click execution script
├── requirements.txt                # Dependency specifications
├── .gitignore                      # Git exclusion rules
├── LICENSE                         # MIT License
└── README.md                       # Master documentation
```

---

## 💻 Technologies Used

- **Language:** Python 3.10+ (Standard Library: `http.server`, `socketserver`, `threading`, `json`, `math`, `urllib`)
- **Frontend:** Vanilla HTML5, Canvas API, CSS3, Modern ES6+ JavaScript
- **Streaming Protocol:** Server-Sent Events (SSE) at 30 FPS with automated REST polling fallback
- **Testing Framework:** Python `unittest` module
- **Optional Tools:** `pytest`, `requests`, `numpy`

---

## 📦 Installation Instructions

### Prerequisites
- Python 3.10 or higher installed.
- Any modern web browser (Google Chrome, Microsoft Edge, Mozilla Firefox, Safari).

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/divyayadav1810/Traffic-light-detection-and-negotiation.git
   cd Traffic-light-detection-and-negotiation
   ```

2. (Optional) Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 How to Run the Project

### Option A: Using the Launcher Script
```bash
python run_app.py
```
*(Optionally specify a custom port: `python run_app.py 8080`)*

### Option B: Windows One-Click
Double-click `start.bat` in the project root directory.

### Accessing the Dashboard
Open your browser and navigate to:
```
http://localhost:8000
```

---

## 🕹️ Interactive Scenarios

| Scenario | Objective | Observed Behavior |
| :--- | :--- | :--- |
| **1: Baseline Clear Approach** | Standard approach under ideal visibility | Vehicle detects green light, maintains cruise speed ($40\text{ km/h}$), or decelerates smoothly if light turns red. |
| **2: Tree-Obstructed Light** | Signal head partially occluded by roadside foliage | Perception confidence dips; sensor fusion tracking memory maintains signal state, avoiding phantom stops. |
| **3: Dilemma Zone (Yellow)** | Signal changes to yellow at critical stopping distance | Controller evaluates stopping distance vs. stop line gap; safely chooses whether to stop or clear intersection. |
| **4: Lead Vehicle Queue** | Slower or stopped lead vehicle ahead | Adaptive Cruise Control engages; ego vehicle stops behind lead car with a $4.5\text{ m}$ buffer. |
| **5: Adverse Weather (Dense Fog)** | Atmospheric haze reduces optical contrast | Detection range contracts; fail-safe defensive pre-braking activates if light status remains unconfirmed. |
| **6: Night Driving & Glare** | Low ambient lighting with active signal bloom | High lamp contrast against night backdrop with illuminated vehicle headlight cones. |

---

## 🖥️ Visual Dashboard Layout

The cockpit dashboard is divided into four dedicated real-time panels:

1. **2.5D Intersection Simulation View (Left):**
   - Top-down perspective showing road lanes, zebra crossings, stop lines ($100\text{ m}$ mark), traffic signal pole ($112\text{ m}$ mark), trees, ego car with illuminated headlights/brake lights, and radar/camera sensor FOV cone.
2. **Windshield Perception HUD (Right Top):**
   - Driver's forward windshield camera feed showing receding roadway, dynamic traffic signal, AI bounding box overlay with `[STATE | CONFIDENCE | DISTANCE]`, and synthetic weather overlays.
3. **Environment & Perception Controls (Right Middle):**
   - Interactive dropdowns to toggle weather conditions, tree occlusion percentage, signal phase modes (Auto / Force Red / Force Yellow / Force Green), and lead vehicles.
4. **Stateflow State Visualizer & Quantitative Metrics (Bottom):**
   - Live highlight of active state: `[CRUISE]` $\rightarrow$ `[DECELERATE]` $\rightarrow$ `[STOPPED]` $\rightarrow$ `[WAITING]` $\rightarrow$ `[PROCEED]` $\rightarrow$ `[CREEP]`.
   - Real-time telemetry gauges displaying Velocity ($\text{km/h}$), Acceleration ($\text{m/s}^2$), Distance to Line ($\text{m}$), and Signal Countdown ($\text{s}$).

---

## 📐 Mathematical Formulation

### Stopping Deceleration Profile
For an ego vehicle at velocity $v$ with remaining distance to the stop buffer $d_{\text{rem}}$:
$$a_{\text{target}} = -\frac{v^2}{2 \cdot \max(0.8, d_{\text{rem}})}$$

### Dilemma Zone Arbitration
Stopping is commanded if:
$$d_{\text{rem}} \ge v \cdot \tau_{\text{react}} + \frac{v^2}{2 \cdot |a_{\text{comf}}|}$$
Otherwise, the vehicle safely proceeds to clear the intersection.

*For complete kinematic derivations and Koschmieder's law, refer to [docs/mathematical_models.md](docs/mathematical_models.md).*

---

## 🧪 Testing

Run the automated test suite directly with Python's built-in test runner:
```bash
python -m unittest discover -s tests
```

### Test Coverage Highlights
- `test_perception.py`: Validates bounding box generation, optical range attenuation, fog contrast reduction, and lead car detection.
- `test_state_machine.py`: Confirms cruising speed regulation, red light braking, stop line precision, and dilemma zone decision correctness.
- `test_traffic_controller.py`: Verifies automatic 4-phase cycles, countdown timing, and manual override persistence.

---

## 🔮 Future Improvements

- [ ] **YOLOv8 Real-Time Inference:** Add an option to process live webcam or MP4 video feeds using an ONNX/PyTorch model.
- [ ] **V2X (Vehicle-to-Infrastructure) DSRC Protocol:** Support SAE J2735 SPaT (Signal Phase and Timing) and MAP messages.
- [ ] **3D WebGL / Three.js Renderer:** Extend the 2.5D canvas to a fully photorealistic 3D cockpit scene with PBR materials.
- [ ] **Multi-Lane Multi-Signal Intersection:** Support dedicated left-turn and right-turn green arrows with cross-traffic yielding.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
