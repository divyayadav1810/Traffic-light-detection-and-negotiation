# Mathematical Models & Kinematics Formulation

This document details the governing mathematical formulations implemented in the simulation and control engine.

---

## 1. Longitudinal Vehicle Kinematics

The vehicle's state is evolved using Euler forward integration:

$$v_{t+1} = \max\left(0, v_t + a_t \cdot \Delta t\right)$$
$$x_{t+1} = x_t + v_t \cdot \Delta t$$

### Jerk-Limited Acceleration
To prevent instantaneous shock and ensure passenger comfort, acceleration changes are rate-limited:

$$\Delta a = \text{clamp}\left(a_{\text{target}} - a_t, -j_{\max} \cdot \Delta t, j_{\max} \cdot \Delta t\right)$$
$$a_{t+1} = a_t + \Delta a$$

Where:
- Maximum jerk limit: $j_{\max} = 4.5\text{ m/s}^3$
- Maximum comfortable deceleration: $a_{\text{comf}} = -2.6\text{ m/s}^2$
- Emergency deceleration limit: $a_{\text{emerg}} = -5.0\text{ m/s}^2$

---

## 2. Stopping Distance & Braking Profile

For a vehicle traveling at velocity $v$, the total required stopping distance factoring reaction time $\tau_{\text{react}}$ is:

$$d_{\text{stop}} = v \cdot \tau_{\text{react}} + \frac{v^2}{2 \cdot |a_{\text{comf}}|}$$

When targeting a specific stop line position $x_{\text{line}}$ with buffer $d_{\text{buffer}} = 2.5\text{ m}$:

$$d_{\text{rem}} = x_{\text{line}} - x_t - d_{\text{buffer}}$$

The target stopping deceleration profile is computed as:

$$a_{\text{target}} = -\frac{v^2}{2 \cdot \max(0.8, d_{\text{rem}})}$$

---

## 3. Dilemma Zone Formulation

When the traffic signal transitions to **YELLOW**, the vehicle evaluates two competing conditions:

1. **Can the vehicle stop comfortably before the stop line?**
   $$\text{Condition: } d_{\text{rem}} \ge d_{\text{stop}}$$
   If true $\rightarrow$ **DECELERATE TO STOP**.

2. **Can the vehicle clear the intersection before the signal turns RED?**
   $$\text{Condition: } t_{\text{clear}} = \frac{x_{\text{intersection\_exit}} - x_t}{v_t} \le t_{\text{yellow\_remaining}}$$
   If the vehicle is too close to stop without exceeding $a_{\text{emerg}}$ $\rightarrow$ **CLEAR INTERSECTION (PROCEED)**.

---

## 4. Optical Weather Attenuation (Koschmieder's Law)

Under dense fog or atmospheric haze, optical contrast attenuates exponentially with distance according to Koschmieder's relation:

$$C(d) = C_0 \cdot e^{-\beta \cdot d}$$

Where:
- $C_0$: Inherent contrast at zero range
- $d$: Distance to traffic signal in meters
- $\beta$: Atmospheric extinction coefficient ($\beta \approx 0.035\text{ m}^{-1}$ for dense fog)

---

## 5. Car-Following / Adaptive Cruise Control (ACC) Safety Buffer

When a lead vehicle is detected at position $x_{\text{lead}}$, the safe following headway distance is:

$$d_{\text{safe}} = d_0 + v_t \cdot T_{\text{headway}}$$

Where:
- $d_0 = 4.5\text{ m}$ (minimum stationary safety gap)
- $T_{\text{headway}} = 1.4\text{ s}$ (time headway)
