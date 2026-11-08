import unittest
from api import handle_request

class ApiTests(unittest.TestCase):
    def test_simulation_returns_real_response(self):
        result = handle_request('/api/simulate', {})
        self.assertEqual(len(result['response']['time']), 501)
        self.assertGreater(result['response']['speed'][-1], 900)
        self.assertIn('iae', result['metrics'])

    def test_invalid_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Resistance'):
            handle_request('/api/simulate', {'motor': {'resistance': 0}})

    def test_optimization_returns_history(self):
        result = handle_request('/api/optimize', {'duration': 1, 'settings': {'popsize': 2, 'generations': 1}})
        self.assertEqual(len(result['history']), result['generations'])
        self.assertGreaterEqual(result['fitness'], 0)
