"""PID in rad/s: u=Kp*e+Ki*integral(e)-Kd*filtered(d omega/dt)."""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class PID:
    kp: float = 0.2
    ki: float = 1.0
    kd: float = 0.0

def controller_terms(error, integral, derivative, speed, pid, voltage_limit):
    """Derivative is a low-pass estimate of speed derivative; suppress kick.

    Back-calculation feeds the saturation difference into the integrator,
    unwinding accumulated error with a 0.1 s tracking time.
    """
    raw = pid.kp * error + pid.ki * integral - pid.kd * derivative
    voltage = float(np.clip(raw, -voltage_limit, voltage_limit))
    integral_rate = error + (voltage - raw) / (0.1 * pid.ki) if pid.ki > 0 else 0.0
    return voltage, integral_rate, raw
