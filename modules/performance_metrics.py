"""Sampled response metrics. Times are measured from the simulation start."""
import numpy as np

def calculate_metrics(time, speed, reference):
    """10–90% first crossings; 2% settling requires all remaining samples.

    Settling is unconfirmed when the last sample lies outside the band. Zero
    reference has undefined relative rise, settling and overshoot. Signed final
    error is reference minus final sample. IAE is trapezoidal in RPM seconds.
    """
    t, y = np.asarray(time), np.asarray(speed)
    if len(t) < 2 or len(t) != len(y) or not np.isfinite(t).all() or not np.isfinite(y).all() or not np.isfinite(reference) or np.any(np.diff(t) <= 0):
        raise ValueError('Response must contain finite samples at increasing times.')
    rise = settling = overshoot = None
    if reference > 0:
        lo, hi = np.flatnonzero(y >= .1*reference), np.flatnonzero(y >= .9*reference)
        if len(lo) and len(hi): rise = float(t[hi[0]]-t[lo[0]])
        outside = np.flatnonzero(np.abs(y-reference) > .02*reference)
        if not len(outside): settling = float(t[0])
        elif outside[-1] < len(t)-1: settling = float(t[outside[-1]+1])
        overshoot = float(max(0, (np.max(y)-reference)/reference*100))
    return {'rise_time': rise, 'settling_time': settling, 'overshoot': overshoot,
            'steady_state_error': float(reference-y[-1]),
            'iae': float(np.trapezoid(np.abs(reference-y), t))}
