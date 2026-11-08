"""SciPy differential evolution over PID gains; fitness is dimensionless."""
from dataclasses import dataclass
import time
import numpy as np
from scipy.optimize import differential_evolution
from modules.dc_motor import simulate
from modules.pid_controller import PID
from modules.performance_metrics import calculate_metrics
from utils.validation import validate_optimization

@dataclass
class OptimizationResult:
    pid: PID
    fitness: float
    generations: int
    success: bool
    message: str
    seconds: float
    history: list

def objective(gains, motor, reference, duration):
    """Weights: normalized IAE 1, overshoot fraction 2, settling 1, final error 2.

    Never-settled responses receive twice the duration as settling penalty.
    Numerical failures receive 1e6. Zero setpoint uses 1 RPM as scale.
    """
    try:
        response = simulate(motor, PID(*gains), reference, duration, samples=301)
        m = calculate_metrics(response['time'], response['speed'], reference)
        scale = max(abs(reference), 1.0)
        if np.max(np.abs(response['speed'])) > max(100*scale, 100000): return 1e6
        value = (m['iae']/(scale*duration) + 2*(m['overshoot'] or 0)/100
                 + (m['settling_time'] if m['settling_time'] is not None else 2*duration)/duration
                 + 2*abs(m['steady_state_error'])/scale)
        return float(value) if np.isfinite(value) else 1e6
    except (ValueError, ArithmeticError, RuntimeError, OverflowError):
        return 1e6

def optimize(motor, reference, duration, bounds, popsize=8, generations=20, mutation=0.7, crossover=0.7, seed=42, progress=None):
    validate_optimization(bounds, popsize, generations, mutation, crossover)
    from utils.validation import validate_simulation
    validate_simulation(motor, PID(), reference, duration)
    history = []
    start = time.perf_counter()
    def callback(x, convergence):
        value = objective(x, motor, reference, duration)
        history.append(value)
        if progress: progress(len(history), generations, value)
        return False
    result = differential_evolution(objective, bounds, args=(motor, reference, duration), popsize=popsize,
                                    maxiter=generations, mutation=mutation, recombination=crossover,
                                    seed=seed, callback=callback, polish=False, workers=1)
    if not np.isfinite(result.fun) or result.fun >= 1e6: raise ValueError('Optimization did not find a valid controller.')
    return OptimizationResult(PID(*map(float, result.x)), float(result.fun), int(result.nit), bool(result.success), str(result.message), time.perf_counter()-start, history)
