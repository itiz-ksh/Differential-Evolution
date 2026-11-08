"""Validate physical and optimization inputs before numerical work."""
import math

def validate_simulation(motor, pid, reference, duration):
    values = vars(motor)
    if not all(math.isfinite(v) for v in list(values.values()) + list(vars(pid).values()) + [reference, duration]):
        raise ValueError('All inputs must be finite numbers.')
    for key in ('resistance', 'inductance', 'torque_constant', 'back_emf', 'inertia', 'max_voltage'):
        if values[key] <= 0: raise ValueError(f'{key.replace("_", " ").title()} must be positive.')
    if motor.friction < 0: raise ValueError('Viscous friction must be non-negative.')
    if any(v < 0 for v in vars(pid).values()): raise ValueError('PID gains must be non-negative.')
    if reference < 0: raise ValueError('Desired speed must be non-negative.')
    if duration <= 0: raise ValueError('Simulation duration must be positive.')

def validate_optimization(bounds, popsize, generations, mutation, crossover):
    if len(bounds) != 3 or any(not math.isfinite(a) or not math.isfinite(b) or a < 0 or a >= b for a,b in bounds):
        raise ValueError('Each gain bound must be finite, non-negative, and lower than its upper bound.')
    if popsize < 1 or generations < 1: raise ValueError('Population multiplier and generations must be positive integers.')
    if not 0 <= mutation < 2: raise ValueError('Mutation must be at least 0 and less than 2.')
    if not 0 <= crossover <= 1: raise ValueError('Crossover must be between 0 and 1.')
