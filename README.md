# Differential Evolution Experiment Lab

This project lets you explore how different search methods find better settings for three simulated engineering problems: controlling a DC motor, finding the best voltage for a solar panel, and controlling the temperature of a heater.

You can change the conditions, try a setting yourself, and watch three methods compete in an **Algorithm Race**: Differential Evolution (DE), particle swarm optimization (PSO), and random search. The graphs show what each method finds and how the simulated system responds.

## The three experiments

| Experiment | What you can set | What the search tries to find |
| --- | --- | --- |
| **DC motor** | Motor properties, target speed, simulation time, and the range of controller settings | PID gains that bring the motor close to its target speed while balancing speed, overshoot, and error |
| **Solar panel** | Light level and whether part of the panel is shaded | A voltage that gives the most power on the simulated curve |
| **Temperature control** | Room temperature, target temperature, heater power, heat loss, and simulation time | PID gains that bring the heater close to its target with low error and overshoot |

A PID controller uses three settings: **Kp** responds to the current error, **Ki** responds to error that has built up over time, and **Kd** responds to how quickly the measured value is changing. Together they determine how strongly the controller acts.

## How Differential Evolution works

DE starts with a group of possible answers. For example, each answer for the motor contains three PID gains. It creates new answers by combining differences between existing ones, mixes the new values with an existing answer, and keeps the better result. It repeats these steps over several rounds, called generations.

The other methods in the race work differently: PSO moves possible answers using their own past results and the best result found by the group; random search simply tries randomly chosen settings. None of the methods is guaranteed to find the best possible answer every time.

## Run the project

You need Python 3.10 or newer and Node.js installed.

1. Open a terminal in the project folder and start the Python part:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python api.py
   ```

2. Open a second terminal in the project folder and start the interface:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Open the address shown in the second terminal, usually [http://127.0.0.1:5173](http://127.0.0.1:5173). Keep both terminals running while you use the app.

The app runs locally on your computer. Results are held in the browser and are lost when the page is refreshed.

## Using the app

1. On **Dashboard**, choose DC motor, solar panel, or temperature control from the application menu.
2. Open **Configuration** and set the conditions for that experiment. The same settings are used in the race.
3. Open **Manual Tuning** to try your own PID gains or solar voltage and view the result.
4. For the motor or solar panel, open **Automatic Optimization** to let DE search for a better setting. For temperature control, use the Algorithm Race to search.
5. Open **Algorithm Race** to compare DE, PSO, and random search. Set the population size, number of generations, and random seed, then select **Calculate and play race**. Pause, step through, or replay the results.

Each method in a race starts with the same randomly generated group of answers and is given the same number of evaluations. The race is calculated before playback; the time shown for each method is its full calculation time. Results can differ when you change the seed, settings, or search budget, so a single race does not prove that one method is always best.

## The mathematics behind the experiments

These equations describe the simplified models used in the app. You can use the app without solving them, but they show what each search is trying to improve.

### DC motor

The motor model tracks electrical current `i` and motor speed `ω`:

```text
di/dt = (V − R i − Ke ω) / L
dω/dt = (Kt i − b ω − TL) / J
```

In plain terms, the first equation describes how current changes with applied voltage and motor speed. The second describes how the resulting torque changes the motor's speed while friction and load resist it.

- `V`: applied voltage; `R`: resistance; `L`: inductance
- `Ke`: back-EMF constant; `Kt`: torque constant
- `J`: rotational inertia; `b`: friction; `TL`: load torque

The motor starts at zero speed and current. Physical constants must be positive, except friction may be zero; load torque can be positive or negative. Speed entered in RPM is converted to radians per second for the equations and controller. The equations are solved using SciPy's `solve_ivp`.

The motor controller calculates its requested voltage as:

```text
e = ωref − ω
u_raw = Kp e + Ki ∫e dt − Kd dω_filtered/dt
```

Here, `e` is the difference between target and actual speed. The derivative uses measured speed, with a filter time constant of 0.05 seconds, to reduce a sudden kick when the target changes. The applied voltage `u` is limited to the positive or negative supply voltage. When `Ki > 0`, the controller adjusts the integral using `(u − u_raw)/(0.1 Ki)` to reduce the buildup of error while voltage is limited; the integral is inactive when `Ki = 0`.

For motor tuning, a lower score is better:

```text
score = IAE / (scale × duration)
      + 2 × overshoot_fraction
      + settling_time / duration
      + 2 × |final_error| / scale
scale = max(target speed in RPM, 1)
```

`IAE` is the accumulated absolute speed error. Overshoot measures how far the speed goes above the target; settling time measures how long it takes to stay close to the target within the simulated period. If the response does not settle, the calculation uses twice the simulation duration as a penalty. Invalid or numerically extreme responses receive a score of 1,000,000. At a zero target, relative overshoot contributes zero to the score.

The displayed measurements use sampled results: rise time is the difference between the first 10% and 90% crossings; settling is the first sample after the final sample outside the 2% band, provided the last sample is inside it. The finite simulation cannot prove that the response stays settled afterward. Overshoot is the non-negative excess above a positive target; final error is target minus the final speed sample. IAE is calculated from absolute RPM error over time. Rise, settling, and relative overshoot are undefined for a zero target; unreachable thresholds are shown as not reached.

The motor's separate Automatic Optimization page uses SciPy's DE with adjustable gain ranges, population multiplier, maximum generations, mutation, crossover, and seed. Its extra polishing step is disabled, so the displayed history represents actual DE generations. Reaching the generation limit can still produce a useful answer even when the status says it has not converged.

### Solar panel

The solar example uses a made-up power curve to make the search visible. For voltage `v` between 0 and 40 V:

```text
envelope = v × (40 − v) / 400
power = envelope × shape × irradiance / 1000
```

For uniform light, `shape = 120`. For simulated partial shade:

```text
shape = 75 × exp(−((v − 12) / 4)²)
      + 115 × exp(−((v − 30) / 4.5)²) + 12
```

The shaded curve has multiple peaks, so a search can find a good peak without finding the highest one. Higher irradiance scales the curve upward. This is an illustrative mathematical curve, not a model or measurement of a real panel.

### Temperature control

The heater model starts at the surrounding temperature. Heater power adds heat, while heat escapes faster as the heater gets warmer than its surroundings:

```text
C × dT/dt = heater_power − H × (T − T_ambient)
```

`T` is temperature, `T_ambient` is room temperature, `C` is heat capacity, and `H` is the heat lost per degree above room temperature. Heater power is limited between zero and the configured maximum. A PID controller adjusts this power over time.

For the temperature race, a lower score is better:

```text
score = mean_absolute_error / temperature_gap
      + 2 × overshoot / temperature_gap
      + 2 × |final_error| / temperature_gap
temperature_gap = target_temperature − ambient_temperature
```

The race searches Kp from 0 to 10, Ki from 0 to 1, and Kd from 0 to 10. The target must be above ambient temperature, but it can still be unreachable if the heater cannot overcome the heat loss.

## Limits of the simulations

These examples are for learning, not for designing or operating real equipment. The motor model leaves out effects such as sensor noise, current limits, and power electronics. The solar curve is illustrative. The heater model does not include sensor delays, changing room temperature, or real heater safety controls. Results are also affected by how long each simulation runs and how many settings the search is allowed to try.

## Running the tests

From the project folder, with the Python environment active:

```bash
python -m unittest discover -s tests
node --test frontend/tests/*.test.js
```

The interface uses React, Vite, and Plotly. Python, NumPy, SciPy, and Matplotlib support the simulations and the existing reporting tools.
