# PID Controller Tuning Using Differential Evolution

A local React and Python engineering application for exploring speed control of an armature-controlled DC motor. It compares a manually tuned PID controller with gains found by SciPy's Differential Evolution (DE). The objective is to reduce tracking error, overshoot and settling time without pretending that every optimized metric must improve.

## Problem and objectives

Choose non-negative proportional, integral and derivative gains for a motor subject to a finite supply voltage and constant load torque. Simulate the physical plant, inspect current and voltage, measure the response, optimize gains and export reproducible results. This is an educational model, not a motor drive design or safety assessment.

## Technology and installation

React, Vite, Plotly, Python, NumPy, SciPy, Matplotlib, Python `csv` and Matplotlib `PdfPages` are used. Python 3.10 or newer and Node.js are required.

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python api.py
# In a second terminal:
cd frontend
npm install
npm run dev
```

Run tests with `python -m unittest discover -s tests`. Open the Vite URL shown in the terminal (usually http://127.0.0.1:5173). Keep both terminals running. Results live in the browser session and are lost on refresh. The API is bound to localhost only.

## Mathematical model

The motor has armature current `i` and angular speed `ω`:

- `di/dt = (V − R i − Ke ω) / L`
- `dω/dt = (Kt i − b ω − TL) / J`

`R` is resistance (Ω), `L` inductance (H), `Ke` back EMF constant (V s/rad), `Kt` torque constant (N m/A), `J` inertia (kg m²), `b` viscous friction (N m s/rad) and `TL` constant load torque (N m). Positive values are required for physical constants except friction, which can be zero; load torque is signed. Initial current and speed are zero. RPM is converted to rad/s for the dynamics and controller. `solve_ivp` integrates the coupled continuous states.

## PID and numerical conventions

`e = ωref − ω`, `u_raw = Kp e + Ki ∫e dt − Kd dω_filtered/dt`. Derivative on measurement avoids setpoint kick. A first-order filter with time constant 0.05 s estimates speed derivative. The applied voltage is clipped symmetrically to ± the supply limit. Back-calculation anti-windup feeds `(u − u_raw)/(0.1 Ki)` into the integrator derivative when Ki > 0; the integral is inactive when Ki = 0. Gains therefore use rad/s as the error unit. The motor has no actuator dynamics or discrete sampling model.

Metrics use the sampled output grid: rise time is the difference between the first 10% and 90% crossings; settling is the first sample after the last sample outside the 2% band, provided the final sample is inside. This does not prove that the response remains settled beyond the time horizon. Overshoot is the non-negative excess of the maximum response relative to the positive reference. Steady-state error is the signed reference minus the **final sample**, even if unsettled. IAE is trapezoidal integral of absolute RPM error, in RPM s. Rise, settling and overshoot are undefined for a zero reference. A response that does not reach a threshold or settle is shown as not reached.

## Differential Evolution

SciPy initializes a population, mutates candidates using population differences, crosses them over, selects lower-cost solutions, and stops on convergence or the generation limit. Population multiplier, generations, mutation, crossover, seed and gain bounds are configurable. Polishing is disabled so the displayed final value corresponds to the last actual generation. Results depend on the seed and budget; reaching the generation limit may yield a usable result with `success=False`.

The minimized dimensionless cost is `IAE/(scale × duration) + 2 × overshoot_fraction + settling_time/duration + 2 × |final_error|/scale`, where `scale = max(reference RPM, 1)`. An unsettled response uses `2 × duration` as its settling penalty; invalid or numerically extreme responses cost 1,000,000. At zero reference relative overshoot is treated as zero in the objective. History is measured from the best candidate in each actual generation.

## Usage

1. **Motor Configuration:** adjust the plant and voltage limit.
2. **Manual PID Tuning:** enter gains, reference RPM and duration, then run the simulation. Defaults: 1,000 RPM, 5 s, Kp = 0.2, Ki = 1, Kd = 0, 12 V, R = 1 Ω, L = 0.05 H, Kt = Ke = 0.1, J = 0.01 and b = 0.001. Run the simulation to apply the settings. The display shows sampled speed, voltage and current and measured metrics. If voltage is insufficient for the target, the response may never settle.
3. **Automatic Optimization:** choose gain bounds and DE settings and run the search. The final gains, measured objective, actual history, status and elapsed time are displayed and retained in browser state.
4. **Performance Comparison:** click Run Comparison to simulate both controllers under identical current conditions; changing plant, reference or duration requires a new optimization. Changing manual gains changes the baseline. Improvement uses reduction, including absolute final error; negative values mean deterioration.
5. **Reports and Export:** download actual recorded manual or optimized CSV data and a PDF containing configuration, gains, comparison, response and convergence. CSV exports simulate the current settings when downloaded.

## Architecture

```text
frontend/src/                React interface and styling
api.py                       Local Python JSON and export API
app.py                       Legacy Streamlit interface
modules/dc_motor.py          State equations and numerical integration
modules/pid_controller.py    Filtered PID and anti-windup
modules/performance_metrics.py  Response measurements
modules/differential_evolution.py  Objective and SciPy optimization
modules/visualization.py     Interactive Plotly graphs
modules/report_generator.py  CSV and PDF generation
utils/validation.py          Input checks
assets/custom.css            Dashboard styling
tests/                       Model and workflow tests
```

## Limitations and future work

The model is linear, with constant load and fixed parameters; it omits noise, nonlinear friction, power electronics, thermal effects, current limits and sensor dynamics. Finite sampling and horizon affect metrics. DE may be slow for large populations, long horizons or stiff parameters and may stop at a local solution. Future work could add sampled controllers, disturbance profiles, current limiting, noise and robust tuning across parameter uncertainty.

## Solar maximum-power application

Choose **Solar panel** in the application selector. Configuration sets an illustrative irradiance scale and either uniform light or simulated partial shade. Manual Tuning evaluates a chosen voltage; Automatic Optimization and DE Playground share a seeded DE search over 0–40 V, with 12 candidates per generation. The playground plots the candidates on the same power curve as they move. The search maximizes power and may converge to a local peak, especially under shade.

The curve is a synthetic educational function, not a physical photovoltaic, bypass-diode, or measured panel model. Irradiance scales its power linearly; the shade setting changes its shape. Solar calculations run in the browser and do not affect motor settings. Run frontend tests with `node --test frontend/tests/*.test.js`.

## Experiment race and temperature control

Select DC motor, solar panel, or temperature control on the dashboard. The Algorithm Race compares Differential Evolution (DE/rand/1/bin), particle swarm optimization, and random search using the current application settings, the same seeded starting population, and the same number of objective evaluations per method. The search is computed before playback; the plotted score is the best seen through the selected generation, and the displayed elapsed time measures the full search for each method. The motor uses the configured PID gain bounds and existing motor objective. Solar searches 0–40 V on the same illustrative curve used by the solar page and maximizes power; it is not a photovoltaic device model. 

Temperature control simulates a single thermal mass starting at ambient, with heat loss proportional to its temperature above ambient and heater power limited between zero and the configured maximum. A sampled PID controller is evaluated using normalized mean absolute error plus twice normalized overshoot and twice normalized final error. The race searches Kp in [0,10], Ki in [0,1], and Kd in [0,10]. The simplified model excludes sensor lag, variable ambient conditions, and heater safety mechanisms. A target above ambient can still be unreachable if maximum power is insufficient to offset heat loss.
