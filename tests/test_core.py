import unittest
import numpy as np
from modules.dc_motor import Motor, simulate, motor_derivatives
from modules.pid_controller import PID, controller_terms
from modules.performance_metrics import calculate_metrics

class CoreTests(unittest.TestCase):
    def test_motor_equations(self):
        m = Motor()
        di, dw = motor_derivatives(1, 2, 3, m)
        self.assertAlmostEqual(di, (3-m.resistance-m.back_emf*2)/m.inductance)
        self.assertAlmostEqual(dw, (m.torque_constant-m.friction*2-m.load_torque)/m.inertia)

    def test_saturation_prevents_windup(self):
        voltage, integral_rate, _ = controller_terms(100, 0, 0, 0, PID(2, 1, 0), 12)
        self.assertEqual(voltage, 12)
        self.assertLess(integral_rate, 0)

    def test_metrics_and_never_settled(self):
        t = np.arange(5.)
        m = calculate_metrics(t, np.array([0, 10, 90, 100, 100]), 100)
        self.assertEqual(m['rise_time'], 1)
        self.assertEqual(m['settling_time'], 3)
        self.assertEqual(m['overshoot'], 0)
        self.assertEqual(m['steady_state_error'], 0)
        self.assertIsNone(calculate_metrics(t, np.zeros(5), 100)['settling_time'])

    def test_simulation_finite(self):
        result = simulate(Motor(), PID(0.2, 1, 0), 1000, 2)
        self.assertTrue(np.isfinite(result['speed']).all())
        self.assertLessEqual(np.max(np.abs(result['voltage'])), 12)
        self.assertGreater(result['speed'][-1], 900)

if __name__ == '__main__': unittest.main()
