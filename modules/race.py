"""Reproducible, equal-budget search demonstrations for the configured plants."""
import math
import time
import numpy as np
from modules.differential_evolution import objective
from modules.pid_controller import PID
from utils.validation import validate_optimization, validate_simulation

DEFAULT_TEMP = {'ambient': 20, 'target': 60, 'heat_capacity': 100, 'heat_loss': 1, 'max_power': 100, 'duration': 600}


def temperature_response(settings, gains):
    c = {**DEFAULT_TEMP, **settings}
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in c.values()):
        raise ValueError('Temperature settings must be finite numbers.')
    if c['heat_capacity'] <= 0 or c['heat_loss'] <= 0 or c['max_power'] <= 0 or not 0 < c['duration'] <= 10000:
        raise ValueError('Heat capacity, heat loss, power and duration must be positive; duration must not exceed 10000 s.')
    if c['target'] <= c['ambient']:
        raise ValueError('Target temperature must exceed ambient temperature for this heater model.')
    if len(gains) != 3 or any(not math.isfinite(v) or v < 0 for v in gains):
        raise ValueError('PID gains must be finite and non-negative.')
    dt = c['duration'] / 600
    temp = c['ambient']; integral = 0.; previous = temp
    temperatures = []; powers = []
    for i in range(601):
        error = c['target'] - temp
        derivative = (temp - previous) / dt if i else 0
        raw = gains[0]*error + gains[1]*integral - gains[2]*derivative
        power = min(c['max_power'], max(0., raw))
        temperatures.append(temp); powers.append(power)
        if i < 600:
            if 0 < raw < c['max_power'] or (raw >= c['max_power'] and error < 0) or (raw <= 0 and error > 0):
                integral += error * dt
            previous = temp
            # Exact update for constant power over this sample interval.
            decay = math.exp(-c['heat_loss']*dt/c['heat_capacity'])
            temp = c['ambient'] + (temp-c['ambient'])*decay + power/c['heat_loss']*(1-decay)
    return {'time': [i*dt for i in range(601)], 'temperature': temperatures, 'power': powers, 'reference': [c['target']]*601}


def temp_cost(settings, gains):
    r = temperature_response(settings, gains)
    c = {**DEFAULT_TEMP, **settings}
    scale = c['target']-c['ambient']
    errors = np.abs(np.asarray(r['temperature'])-c['target'])/scale
    overshoot = max(0., max(r['temperature'])-c['target'])/scale
    return float(np.mean(errors) + 2*overshoot + 2*errors[-1])


def solar_power(v, shade, irradiance):
    envelope = v*(40-v)/400
    shape = 75*math.exp(-((v-12)/4)**2)+115*math.exp(-((v-30)/4.5)**2)+12 if shade else 120
    return envelope*shape*irradiance/1000


def run_race(application, motor, reference, duration, settings, race, solar, temp):
    population = int(race.get('population', 6)); generations = int(race.get('generations', 5)); seed = int(race.get('seed', 42))
    if not 4 <= population <= 30 or not 1 <= generations <= 30 or not 0 <= seed <= 2**32-1:
        raise ValueError('Population must be 4–30, generations 1–30, and seed between 0 and 4294967295.')
    bounds = settings.get('bounds', [[0,1],[0,3],[0,.1]]) if application == 'motor' else ([[0,10],[0,1],[0,10]] if application == 'temperature' else [[0,40]])
    if application == 'motor':
        validate_optimization(bounds, 1, 1, .7, .7); validate_simulation(motor, PID(), reference, duration)
        cost = lambda x: objective(x, motor, reference, duration)
    elif application == 'temperature':
        temperature_response(temp, [1,0,0]); cost = lambda x: temp_cost(temp, x)
    elif application == 'solar':
        irradiance = float(solar.get('irradiance',1000)); shade = solar.get('shade',True)
        if not math.isfinite(irradiance) or not 0 <= irradiance <= 1200 or not isinstance(shade, bool): raise ValueError('Invalid solar conditions.')
        cost = lambda x: -solar_power(x[0], shade, irradiance)
    else: raise ValueError('Unknown application.')
    bounds = np.array(bounds, dtype=float); low, high = bounds[:,0], bounds[:,1]; dim = len(low)
    initial = np.random.default_rng(seed).uniform(low, high, size=(population, dim))
    methods = []
    for method in ('de','pso','random'):
        start = time.perf_counter(); rng = np.random.default_rng(seed + {'de':1,'pso':2,'random':3}[method]); points = initial.copy()
        values = np.array([cost(x) for x in points]); personal = points.copy(); personal_values = values.copy()
        velocity = np.zeros_like(points); best_index = int(np.argmin(values)); best = points[best_index].copy(); best_value = float(values[best_index])
        history = [{'evaluations': population, 'cost': best_value, 'position': best.tolist()}]
        for generation in range(generations):
            old = points.copy(); proposals = []
            for i in range(population):
                if method == 'de':
                    a,b,c = rng.choice([j for j in range(population) if j != i], 3, replace=False)
                    mutant = np.clip(old[a]+.7*(old[b]-old[c]), low, high)
                    mask = rng.random(dim)<.7; mask[rng.integers(dim)] = True
                    trial = np.where(mask, mutant, old[i])
                elif method == 'pso':
                    velocity[i] = .7*velocity[i]+1.4*rng.random(dim)*(personal[i]-old[i])+1.4*rng.random(dim)*(best-old[i])
                    trial = np.clip(old[i]+velocity[i], low, high)
                else: trial = rng.uniform(low, high)
                proposals.append(trial)
            proposals = np.array(proposals); trial_values = np.array([cost(x) for x in proposals])
            if method == 'de':
                improved = trial_values <= values; points[improved] = proposals[improved]; values[improved] = trial_values[improved]
            else: points = proposals; values = trial_values
            if method == 'pso':
                improved = values < personal_values; personal[improved] = points[improved]; personal_values[improved] = values[improved]
            idx = int(np.argmin(values))
            if values[idx] < best_value: best_value = float(values[idx]); best = points[idx].copy()
            history.append({'evaluations': population*(generation+2), 'cost': best_value, 'position': best.tolist()})
        methods.append({'method':method, 'evaluations':population*(generations+1), 'seconds':time.perf_counter()-start, 'history':history})
    return {'application':application, 'methods':methods}
