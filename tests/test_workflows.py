import unittest
from dataclasses import replace
from modules.dc_motor import Motor, simulate
from modules.pid_controller import PID
from modules.differential_evolution import optimize
from modules.performance_metrics import calculate_metrics
from modules.report_generator import csv_bytes, pdf_bytes
from utils.validation import validate_optimization

class WorkflowTests(unittest.TestCase):
    def test_optimization_history_and_exports(self):
        motor=replace(Motor(), resistance=1.2)
        original=simulate(motor, PID(), 800, 1)
        opt=optimize(motor, 800, 1, [(0,.8),(0,2),(0,.05)],popsize=2,generations=2,seed=5)
        tuned=simulate(motor,opt.pid,800,1)
        self.assertEqual(len(opt.history),opt.generations)
        self.assertAlmostEqual(opt.history[-1], opt.fitness)
        self.assertTrue(csv_bytes(original).startswith(b'time_s,reference_rpm'))
        self.assertTrue(pdf_bytes(motor,PID(),opt,original,tuned,800,1).startswith(b'%PDF'))

    def test_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError,'Resistance'): simulate(replace(Motor(),resistance=0),PID(),1000,1)
        with self.assertRaisesRegex(ValueError,'duration'): simulate(Motor(),PID(),1000,0)
        with self.assertRaisesRegex(ValueError,'bound'): validate_optimization([(1,0),(0,1),(0,1)],2,2,.7,.7)

    def test_zero_reference_metrics(self):
        m=calculate_metrics([0,1],[0,0],0)
        self.assertIsNone(m['overshoot']); self.assertIsNone(m['settling_time']); self.assertEqual(m['iae'],0)
