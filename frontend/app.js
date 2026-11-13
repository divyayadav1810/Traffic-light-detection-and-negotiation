/**
 * Full-Stack Frontend Client for Traffic Light Negotiation & Perception Detection
 * Connects via Server-Sent Events (SSE) / REST, renders 2.5D Intersection canvas
 * and first-person AI perception windshield HUD with bounding box overlays.
 */

let simState = null;
let isPlaying = true;
let eventSource = null;

// DOM Elements
const simCanvas = document.getElementById("simCanvas");
const simCtx = simCanvas.getContext("2d");
const cameraCanvas = document.getElementById("cameraCanvas");
const camCtx = cameraCanvas.getContext("2d");

const connStatus = document.getElementById("connStatus");
const simPhaseIndicator = document.getElementById("simPhaseIndicator");
const hudEgoPos = document.getElementById("hudEgoPos");
const hudGap = document.getElementById("hudGap");
const hudBrakeDist = document.getElementById("hudBrakeDist");

const btnPlay = document.getElementById("btnPlay");
const btnStep = document.getElementById("btnStep");
const btnReset = document.getElementById("btnReset");
const speedSlider = document.getElementById("speedSlider");
const speedVal = document.getElementById("speedVal");

const stateNodes = {
  CRUISE: document.getElementById("stateCruise"),
  DECELERATE: document.getElementById("stateDecel"),
  STOPPED: document.getElementById("stateStop"),
  WAITING: document.getElementById("stateWait"),
  PROCEED: document.getElementById("stateProceed"),
  CREEP: document.getElementById("stateCreep"),
};
const reasonBanner = document.getElementById("reasonBanner");

const telemSpeed = document.getElementById("telemSpeed");
const telemAccel = document.getElementById("telemAccel");
const telemDistStop = document.getElementById("telemDistStop");
const telemSignalState = document.getElementById("telemSignalState");
const telemSignalTimer = document.getElementById("telemSignalTimer");

const visState = document.getElementById("visState");
const visConf = document.getElementById("visConf");
const visEstDist = document.getElementById("visEstDist");
const fuseState = document.getElementById("fuseState");
const fuseConf = document.getElementById("fuseConf");
const fuseDist = document.getElementById("fuseDist");
const perceptionStatusTag = document.getElementById("perceptionStatusTag");

const weatherSelect = document.getElementById("weatherSelect");
const occlusionSelect = document.getElementById("occlusionSelect");
const signalModeSelect = document.getElementById("signalModeSelect");
const leadCarSelect = document.getElementById("leadCarSelect");

const metricAccuracy = document.getElementById("metricAccuracy");
const metricStopErr = document.getElementById("metricStopErr");
const metricComfort = document.getElementById("metricComfort");
const metricCollisions = document.getElementById("metricCollisions");
const metricStops = document.getElementById("metricStops");

// Connect SSE stream
function initStream() {
  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource("/api/stream");

  eventSource.onopen = () => {
    connStatus.innerText = "STREAM LIVE (30 FPS)";
    connStatus.style.color = "var(--accent-green)";
  };

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      updateState(data);
    } catch (e) {
      console.error("Error parsing telemetry stream:", e);
    }
  };

  eventSource.onerror = () => {
    connStatus.innerText = "POLLING FALLBACK";
    connStatus.style.color = "var(--accent-yellow)";
    // Fallback polling
    setTimeout(pollStatus, 100);
  };
}

async function pollStatus() {
  try {
    const res = await fetch("/api/status");
    if (res.ok) {
      const data = await res.json();
      updateState(data);
    }
  } catch (e) {}
  if (!eventSource || eventSource.readyState !== EventSource.OPEN) {
    setTimeout(pollStatus, 33);
  }
}

// Update UI and trigger renderers
function updateState(data) {
  simState = data;

  // 1. Update Kinematic Values
  const ego = data.ego;
  hudEgoPos.innerText = `${ego.position.toFixed(1)} m`;
  const gap = ego.distance_to_stop_line;
  hudGap.innerText = gap > 0 ? `${gap.toFixed(1)} m` : "CLEARED";
  hudBrakeDist.innerText = `${ego.required_stopping_dist.toFixed(1)} m`;

  telemSpeed.innerText = ego.speed_kmh.toFixed(1);
  telemAccel.innerText = (ego.acceleration >= 0 ? "+" : "") + ego.acceleration.toFixed(2);
  telemDistStop.innerText = gap.toFixed(1);

  // 2. Update Traffic Signal
  const light = data.traffic_light;
  simPhaseIndicator.innerText = `SIGNAL: ${light.state} (${light.time_remaining.toFixed(1)}s)`;
  telemSignalState.innerText = light.state;
  telemSignalTimer.innerText = `${light.time_remaining.toFixed(1)}s left`;

  if (light.state === "RED") {
    telemSignalState.style.color = "var(--accent-red)";
  } else if (light.state === "YELLOW") {
    telemSignalState.style.color = "var(--accent-yellow)";
  } else {
    telemSignalState.style.color = "var(--accent-green)";
  }

  // 3. Update Stateflow FSM
  Object.keys(stateNodes).forEach((k) => {
    if (stateNodes[k]) {
      stateNodes[k].className = "state-node";
    }
  });

  const activeNode = stateNodes[data.state];
  if (activeNode) {
    let colorClass = "";
    if (data.state === "STOPPED" || data.state === "WAITING") colorClass = "red";
    else if (data.state === "DECELERATE") colorClass = "yellow";
    else if (data.state === "PROCEED" || data.state === "CRUISE") colorClass = "green";
    activeNode.className = `state-node active ${colorClass}`;
  }
  reasonBanner.innerText = data.reason;

  // 4. Update Perception HUD Data
  const vis = data.perception.vision;
  const fuse = data.perception.fused;

  visState.innerHTML = `STATE: <strong style="color: ${getColorHex(vis.state)}">${vis.state}</strong>`;
  visConf.innerHTML = `CONF: <strong>${(vis.confidence * 100).toFixed(1)}%</strong>`;
  visEstDist.innerHTML = `OPTICAL DIST: <strong>${vis.estimated_distance ? vis.estimated_distance.toFixed(1) + "m" : "--"}</strong>`;

  fuseState.innerHTML = `FUSED: <strong style="color: ${getColorHex(fuse.state)}">${fuse.state}</strong>`;
  fuseConf.innerHTML = `CONF: <strong>${(fuse.confidence * 100).toFixed(1)}%</strong>`;
  fuseDist.innerHTML = `RADAR RANGE: <strong>${fuse.distance ? fuse.distance.toFixed(1) + "m" : "--"}</strong>`;

  perceptionStatusTag.innerText = `STATUS: ${fuse.tracking_status}`;
  perceptionStatusTag.style.color = fuse.tracking_status === "LOCKED" ? "var(--accent-green)" : "var(--accent-yellow)";

  // 5. Update Metrics Summary
  if (data.metrics_summary) {
    const m = data.metrics_summary;
    metricAccuracy.innerText = `${m.perception_accuracy_percent.toFixed(1)}%`;
    metricStopErr.innerText = `${m.mean_stop_error_meters.toFixed(2)} m`;
    metricComfort.innerText = `${m.comfort_compliance ? "100% compliant" : "Harsh braking recorded"}`;
    metricCollisions.innerText = `${m.collisions} (Clean)`;
    metricStops.innerText = `${m.successful_stops}`;
  }

  // 6. Draw Views
  renderIntersection(data);
  renderCameraView(data);
}

function getColorHex(state) {
  if (state === "RED") return "var(--accent-red)";
  if (state === "YELLOW") return "var(--accent-yellow)";
  if (state === "GREEN") return "var(--accent-green)";
  return "var(--text-secondary)";
}

// ----------------------------------------------------
// 2.5D INTERSECTION CANVAS RENDERER
// ----------------------------------------------------
function renderIntersection(data) {
  const w = simCanvas.width;
  const h = simCanvas.height;
  simCtx.clearRect(0, 0, w, h);

  // Background Grass / Urban Surface
  simCtx.fillStyle = "#111823";
  simCtx.fillRect(0, 0, w, h);

  // Road Configuration (Mapping 0 to 140 meters along road)
  // Stop line at 100m, intersection box from 100m to 125m
  const roadY = h / 2 - 45;
  const roadHeight = 90;

  // Road Surface (Dark Asphalt)
  simCtx.fillStyle = "#1e2638";
  simCtx.fillRect(0, roadY, w, roadHeight);

  // Sidewalks
  simCtx.fillStyle = "#2c384e";
  simCtx.fillRect(0, roadY - 14, w, 14);
  simCtx.fillRect(0, roadY + roadHeight, w, 14);

  // Road scale: road spans x from 30px (0m) to 870px (130m)
  const xOrigin = 40;
  const roadPixelLength = w - 100;
  const maxMeter = 130.0;
  function meterToPixel(m) {
    return xOrigin + (m / maxMeter) * roadPixelLength;
  }

  // Lane Divider (Dashed Yellow/White)
  simCtx.strokeStyle = "#5a6e8c";
  simCtx.lineWidth = 2;
  simCtx.setLineDash([12, 10]);
  simCtx.beginPath();
  simCtx.moveTo(0, roadY + roadHeight / 2);
  simCtx.lineTo(meterToPixel(98), roadY + roadHeight / 2);
  simCtx.stroke();
  simCtx.setLineDash([]);

  // Crosswalk (Zebra Stripes at 100m - 104m)
  const stopX = meterToPixel(100.0);
  simCtx.fillStyle = "rgba(255, 255, 255, 0.75)";
  for (let y = roadY + 4; y < roadY + roadHeight - 4; y += 14) {
    simCtx.fillRect(stopX + 2, y, 16, 7);
  }

  // Solid White Stop Line at 100m
  simCtx.fillStyle = "#ffffff";
  simCtx.fillRect(stopX - 4, roadY + roadHeight / 2, 5, roadHeight / 2);

  // Stop line label
  simCtx.fillStyle = "#8c9cb8";
  simCtx.font = "10px monospace";
  simCtx.fillText("STOP LINE (100m)", stopX - 25, roadY + roadHeight + 28);

  // Distance markers along road
  for (let m = 0; m <= 120; m += 20) {
    const mx = meterToPixel(m);
    simCtx.fillStyle = "rgba(140, 156, 184, 0.35)";
    simCtx.fillRect(mx, roadY + roadHeight, 1, 6);
    simCtx.fillText(`${m}m`, mx - 8, roadY + roadHeight + 18);
  }

  // Cross Street (Vertical Intersection Road at 104m to 124m)
  const crossX = meterToPixel(105);
  const crossW = meterToPixel(123) - crossX;
  simCtx.fillStyle = "#1e2638";
  simCtx.fillRect(crossX, 0, crossW, h);

  // Traffic Light Tower (Positioned at 112m, on corner sidewalk)
  const lightX = meterToPixel(112.0);
  const lightY = roadY - 40;
  drawTrafficLightTower(simCtx, lightX, lightY, data.traffic_light.state);

  // Tree Obstruction (if enabled or present near 70m-80m)
  const treeX = meterToPixel(78.0);
  const treeY = roadY - 32;
  const isOccluded = data.perception.vision.occlusion_ratio > 0.05;
  drawTree(simCtx, treeX, treeY, isOccluded);

  // Draw Lead Vehicle (if enabled)
  if (data.lead_car.enabled && data.lead_car.position !== null) {
    const leadX = meterToPixel(data.lead_car.position);
    drawCar(simCtx, leadX, roadY + roadHeight * 0.70, "#4a90e2", false, "Lead Car");
  }

  // Draw Ego Vehicle
  const egoPos = data.ego.position;
  const egoX = meterToPixel(egoPos);
  const egoY = roadY + roadHeight * 0.70;
  const isBraking = data.state === "DECELERATE" || data.state === "STOPPED";
  drawCar(simCtx, egoX, egoY, "#00d2ff", isBraking, "EGO VEHICLE");

  // Ego Sensor Field of View (Camera & Radar Cone)
  drawSensorCone(simCtx, egoX, egoY);

  // Required Stopping Distance projection line
  if (egoPos < 100.0 && data.ego.required_stopping_dist > 1.0) {
    const targetStopPx = meterToPixel(egoPos + data.ego.required_stopping_dist);
    simCtx.strokeStyle = "rgba(255, 184, 0, 0.6)";
    simCtx.lineWidth = 2;
    simCtx.setLineDash([4, 4]);
    simCtx.beginPath();
    simCtx.moveTo(egoX + 22, egoY + 22);
    simCtx.lineTo(targetStopPx, egoY + 22);
    simCtx.stroke();
    simCtx.setLineDash([]);
  }
}

function drawCar(ctx, x, y, bodyColor, isBraking, label) {
  ctx.save();
  ctx.translate(x, y);

  // Shadow
  ctx.fillStyle = "rgba(0,0,0,0.45)";
  ctx.fillRect(-20, -10, 44, 20);

  // Car Body
  ctx.fillStyle = bodyColor;
  ctx.beginPath();
  ctx.roundRect(-18, -9, 38, 18, 4);
  ctx.fill();

  // Windshield & Windows
  ctx.fillStyle = "#0c131f";
  ctx.fillRect(-6, -7, 14, 14);

  // Headlights (Front is pointing to right)
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(18, -8, 3, 4);
  ctx.fillRect(18, 4, 3, 4);

  // Headlight Light Beam
  const beamGrad = ctx.createLinearGradient(21, 0, 90, 0);
  beamGrad.addColorStop(0, "rgba(255, 255, 255, 0.35)");
  beamGrad.addColorStop(1, "rgba(255, 255, 255, 0.0)");
  ctx.fillStyle = beamGrad;
  ctx.beginPath();
  ctx.moveTo(21, -8);
  ctx.lineTo(85, -20);
  ctx.lineTo(85, 20);
  ctx.lineTo(21, 8);
  ctx.closePath();
  ctx.fill();

  // Brake Lights (Red on rear)
  ctx.fillStyle = isBraking ? "#ff0033" : "rgba(255, 0, 51, 0.35)";
  ctx.fillRect(-20, -8, 3, 4);
  ctx.fillRect(-20, 4, 3, 4);
  if (isBraking) {
    ctx.shadowColor = "#ff0033";
    ctx.shadowBlur = 10;
    ctx.fillRect(-20, -8, 3, 4);
    ctx.fillRect(-20, 4, 3, 4);
    ctx.shadowBlur = 0;
  }

  // Car Label
  ctx.fillStyle = "#f0f4f8";
  ctx.font = "9px monospace";
  ctx.fillText(label, -22, -14);

  ctx.restore();
}

function drawSensorCone(ctx, x, y) {
  ctx.save();
  const coneGrad = ctx.createRadialGradient(x + 20, y, 10, x + 160, y, 140);
  coneGrad.addColorStop(0, "rgba(0, 210, 255, 0.22)");
  coneGrad.addColorStop(1, "rgba(0, 210, 255, 0.0)");

  ctx.fillStyle = coneGrad;
  ctx.beginPath();
  ctx.moveTo(x + 18, y);
  ctx.lineTo(x + 150, y - 48);
  ctx.lineTo(x + 150, y + 48);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function drawTrafficLightTower(ctx, x, y, state) {
  ctx.save();
  // Pole
  ctx.fillStyle = "#4a5568";
  ctx.fillRect(x - 2, y, 4, 35);

  // Housing Box
  ctx.fillStyle = "#0f172a";
  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(x - 8, y - 28, 16, 32, 3);
  ctx.fill();
  ctx.stroke();

  // Red Bulb
  ctx.fillStyle = state === "RED" ? "#ff3366" : "#44111e";
  if (state === "RED") { ctx.shadowColor = "#ff3366"; ctx.shadowBlur = 10; }
  ctx.beginPath();
  ctx.arc(x, y - 21, 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  // Yellow Bulb
  ctx.fillStyle = state === "YELLOW" ? "#ffb800" : "#443410";
  if (state === "YELLOW") { ctx.shadowColor = "#ffb800"; ctx.shadowBlur = 10; }
  ctx.beginPath();
  ctx.arc(x, y - 12, 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  // Green Bulb
  ctx.fillStyle = state === "GREEN" ? "#00ff88" : "#0f3822";
  if (state === "GREEN") { ctx.shadowColor = "#00ff88"; ctx.shadowBlur = 10; }
  ctx.beginPath();
  ctx.arc(x, y - 3, 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  ctx.restore();
}

function drawTree(ctx, x, y, isOccluded) {
  ctx.save();
  // Trunk
  ctx.fillStyle = "#5c4033";
  ctx.fillRect(x - 3, y + 6, 6, 18);

  // Foliage Canopy
  ctx.fillStyle = isOccluded ? "#2d6a4f" : "#1b4332";
  ctx.beginPath();
  ctx.arc(x, y, 16, 0, Math.PI * 2);
  ctx.arc(x + 10, y + 3, 14, 0, Math.PI * 2);
  ctx.arc(x - 8, y + 4, 12, 0, Math.PI * 2);
  ctx.fill();

  if (isOccluded) {
    ctx.fillStyle = "#ffb800";
    ctx.font = "8px monospace";
    ctx.fillText("🌲 OBSTRUCTION", x - 26, y - 18);
  }
  ctx.restore();
}

// ----------------------------------------------------
// ONBOARD WINDSHIELD PERCEPTION HUD RENDERER
// ----------------------------------------------------
function renderCameraView(data) {
  const w = cameraCanvas.width;
  const h = cameraCanvas.height;
  camCtx.clearRect(0, 0, w, h);

  const weather = data.perception.vision;
  const isNight = weather.glare > 0.4;
  const isFog = weather.contrast < 0.6;

  // Sky & Horizon
  if (isNight) {
    camCtx.fillStyle = "#03060c";
  } else if (isFog) {
    camCtx.fillStyle = "#707b8a";
  } else {
    camCtx.fillStyle = "#22354e";
  }
  camCtx.fillRect(0, 0, w, h * 0.55);

  // Asphalt Road (Perspective Trapezoid)
  camCtx.fillStyle = isNight ? "#0d131d" : "#242d3d";
  camCtx.beginPath();
  camCtx.moveTo(w * 0.45, h * 0.55);
  camCtx.lineTo(w * 0.55, h * 0.55);
  camCtx.lineTo(w * 0.95, h);
  camCtx.lineTo(w * 0.05, h);
  camCtx.closePath();
  camCtx.fill();

  // Lane Markings receding
  camCtx.strokeStyle = "rgba(255, 255, 255, 0.6)";
  camCtx.lineWidth = 2;
  camCtx.beginPath();
  camCtx.moveTo(w * 0.5, h * 0.55);
  camCtx.lineTo(w * 0.5, h);
  camCtx.stroke();

  // Stop line on horizon road
  const distToStop = data.ego.distance_to_stop_line;
  if (distToStop > 0 && distToStop < 90) {
    const normDist = Math.max(0, distToStop / 90.0);
    const stopLineY = h * 0.55 + (1.0 - normDist) * (h * 0.42);
    const lineW = (1.0 - normDist) * (w * 0.7) + (w * 0.1);
    camCtx.fillStyle = "rgba(255, 255, 255, 0.85)";
    camCtx.fillRect((w - lineW) / 2, stopLineY, lineW, 3);
  }

  // Draw Traffic Light in Camera View
  const lightDist = data.perception.fused.distance || distToStop + 12;
  if (lightDist > 2.0 && lightDist < 110) {
    const scale = Math.max(0.12, Math.min(1.0, 1.0 - (lightDist / 110.0)));
    const lightH = 20 + scale * 90;
    const lightW = lightH * 0.36;
    const lightX = w * 0.58 + scale * 60;
    const lightY = h * 0.52 - lightH * 0.8;

    // Housing
    camCtx.fillStyle = "#111827";
    camCtx.strokeStyle = "#374151";
    camCtx.lineWidth = 2;
    camCtx.beginPath();
    camCtx.roundRect(lightX - lightW / 2, lightY, lightW, lightH, 3);
    camCtx.fill();
    camCtx.stroke();

    const bulbRadius = lightW * 0.32;
    const bulbStates = ["RED", "YELLOW", "GREEN"];
    const curState = data.traffic_light.state;

    bulbStates.forEach((st, idx) => {
      const by = lightY + (idx + 1) * (lightH / 4);
      let bulbColor = "#222";
      let halo = false;

      if (st === curState) {
        halo = true;
        if (st === "RED") bulbColor = "#ff3366";
        if (st === "YELLOW") bulbColor = "#ffb800";
        if (st === "GREEN") bulbColor = "#00ff88";
      }

      if (halo) {
        camCtx.save();
        camCtx.shadowColor = bulbColor;
        camCtx.shadowBlur = isNight ? 24 : 12;
        camCtx.fillStyle = bulbColor;
        camCtx.beginPath();
        camCtx.arc(lightX, by, bulbRadius, 0, Math.PI * 2);
        camCtx.fill();
        camCtx.restore();
      } else {
        camCtx.fillStyle = bulbColor;
        camCtx.beginPath();
        camCtx.arc(lightX, by, bulbRadius, 0, Math.PI * 2);
        camCtx.fill();
      }
    });

    // Tree Foliage Occlusion Overlay (if active)
    if (data.perception.vision.occlusion_ratio > 0.05) {
      camCtx.fillStyle = "rgba(22, 60, 36, 0.88)";
      camCtx.beginPath();
      camCtx.arc(lightX - lightW * 0.4, lightY + lightH * 0.3, lightW * 1.2, 0, Math.PI * 2);
      camCtx.fill();
    }

    // AI Computer Vision Bounding Box Overlay
    if (data.perception.vision.detected) {
      const pad = 6;
      const bx = lightX - lightW / 2 - pad;
      const by = lightY - pad;
      const bw = lightW + pad * 2;
      const bh = lightH + pad * 2;

      camCtx.save();
      camCtx.strokeStyle = "#00d2ff";
      camCtx.lineWidth = 2;
      camCtx.strokeRect(bx, by, bw, bh);

      // Corner Reticles
      const cl = 6;
      camCtx.strokeStyle = "#ffffff";
      camCtx.lineWidth = 2.5;
      camCtx.beginPath();
      // Top-left
      camCtx.moveTo(bx, by + cl); camCtx.lineTo(bx, by); camCtx.lineTo(bx + cl, by);
      // Top-right
      camCtx.moveTo(bx + bw - cl, by); camCtx.lineTo(bx + bw, by); camCtx.lineTo(bx + bw, by + cl);
      // Bottom-left
      camCtx.moveTo(bx, by + bh - cl); camCtx.lineTo(bx, by + bh); camCtx.lineTo(bx + cl, by + bh);
      // Bottom-right
      camCtx.moveTo(bx + bw - cl, by + bh); camCtx.lineTo(bx + bw, by + bh); camCtx.lineTo(bx + bw, by + bh - cl);
      camCtx.stroke();

      // Bounding Box Tag Label
      const tagText = `${data.perception.vision.state} | ${(data.perception.vision.confidence * 100).toFixed(0)}% | ${lightDist.toFixed(1)}m`;
      camCtx.fillStyle = "rgba(0, 210, 255, 0.9)";
      camCtx.fillRect(bx, by - 16, camCtx.measureText(tagText).width + 12, 16);
      camCtx.fillStyle = "#000000";
      camCtx.font = "bold 9px monospace";
      camCtx.fillText(tagText, bx + 6, by - 4);
      camCtx.restore();
    }
  }

  // Weather Overlays (Fog mist or Rain streaks)
  if (isFog) {
    camCtx.fillStyle = "rgba(200, 210, 225, 0.45)";
    camCtx.fillRect(0, 0, w, h);
  }

  // Windshield Crosshairs
  camCtx.strokeStyle = "rgba(0, 210, 255, 0.25)";
  camCtx.lineWidth = 1;
  camCtx.beginPath();
  camCtx.moveTo(w / 2 - 15, h / 2);
  camCtx.lineTo(w / 2 + 15, h / 2);
  camCtx.moveTo(w / 2, h / 2 - 15);
  camCtx.lineTo(w / 2, h / 2 + 15);
  camCtx.stroke();
}

// ----------------------------------------------------
// UI CONTROLS & EVENT LISTENERS
// ----------------------------------------------------
btnPlay.addEventListener("click", async () => {
  isPlaying = !isPlaying;
  btnPlay.innerText = isPlaying ? "⏸ Pause" : "▶ Play";
  await fetch("/api/play", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ running: isPlaying })
  });
});

btnStep.addEventListener("click", async () => {
  await fetch("/api/step", { method: "POST" });
});

btnReset.addEventListener("click", async () => {
  const spd = parseFloat(speedSlider.value);
  await fetch("/api/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speed_kmh: spd })
  });
});

speedSlider.addEventListener("input", async (e) => {
  const spd = e.target.value;
  speedVal.innerText = `${spd} km/h`;
  await fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speed_kmh: spd })
  });
});

weatherSelect.addEventListener("change", async (e) => {
  await fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ weather: e.target.value })
  });
});

occlusionSelect.addEventListener("change", async (e) => {
  await fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ occlusion: parseFloat(e.target.value) })
  });
});

signalModeSelect.addEventListener("change", async (e) => {
  await fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ light_state: e.target.value })
  });
});

leadCarSelect.addEventListener("change", async (e) => {
  await fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lead_vehicle: e.target.value === "true" })
  });
});

// Scenario buttons
document.querySelectorAll(".scenario-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    document.querySelectorAll(".scenario-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const scenario = btn.getAttribute("data-scenario");
    await fetch("/api/scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: scenario })
    });
  });
});

// Boot stream
initStream();

