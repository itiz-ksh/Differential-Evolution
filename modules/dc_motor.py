"""Armature controlled DC motor and continuous closed-loop integration."""
from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp
from modules.pid_controller import controller_terms

@dataclass(frozen=True)
class Motor:
    resistance: float = 1.0
    inductance: float = 0.05
    torque_constant: float = 0.1
    back_emf: float = 0.1
    inertia: float = 0.01
    friction: float = 0.001
    max_voltage: float = 12.0
    load_torque: float = 0.0

def motor_derivatives(current, omega, voltage, motor):
    """di/dt=(V-Ri-Ke*omega)/L; domega/dt=(Kt*i-b*omega-TL)/J."""
    return ((voltage - motor.resistance*current - motor.back_emf*omega)/motor.inductance,
            (motor.torque_constant*current - motor.friction*omega - motor.load_torque)/motor.inertia)

def simulate(motor, pid, reference_rpm, duration, samples=501):
    """Integrate current, speed, error integral, and filtered speed derivative.

    A first-order filter estimates dω/dt with time constant 0.05 s.
    All gains operate on rad/s and voltage, not RPM.
    """
    from utils.validation import validate_simulation
    validate_simulation(motor, pid, reference_rpm, duration)
    reference = reference_rpm * 2*np.pi/60
    tau = 0.05
    def rhs(t, state):
        current, omega, integral, filtered_speed = state
        derivative = (omega-filtered_speed)/tau
        voltage, integral_rate, _ = controller_terms(reference-omega, integral, derivative, omega, pid, motor.max_voltage)
        di, dw = motor_derivatives(current, omega, voltage, motor)
        return [di, dw, integral_rate, derivative]
    t = np.linspace(0, duration, samples)
    solution = solve_ivp(rhs, (0, duration), [0, 0, 0, 0], t_eval=t, rtol=1e-5, atol=1e-7)
    if not solution.success or solution.y.shape != (4, samples) or not np.isfinite(solution.y).all():
        raise ValueError('Numerical integration failed or produced non-finite values.')
    current, omega, integral, filtered_speed = solution.y
    voltage = np.array([controller_terms(reference-w, integ, (w-f)/tau, w, pid, motor.max_voltage)[0] for w, integ, f in zip(omega, integral, filtered_speed)])
    speed = omega*60/(2*np.pi)
    return {'time': t, 'reference': np.full_like(t, reference_rpm), 'speed': speed,
            'current': current, 'voltage': voltage, 'error': reference_rpm-speed}
