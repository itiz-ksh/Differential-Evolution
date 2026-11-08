import unittest
from api import handle_request

class RaceTests(unittest.TestCase):
    def test_temperature_responds_to_heating_and_conditions(self):
        result = handle_request('/api/temperature', {'temperature': {'ambient': 20, 'target': 60}, 'pid': {'kp': 4, 'ki': 0.2, 'kd': 0}})
        self.assertGreater(result['response']['temperature'][-1], 20)
        self.assertEqual(result['response']['reference'][0], 60)

    def test_race_has_equal_budgets_and_reproducible_searches(self):
        payload = {'application': 'temperature', 'race': {'population': 4, 'generations': 1, 'seed': 42}}
        first = handle_request('/api/race', payload)
        second = handle_request('/api/race', payload)
        self.assertEqual([x['method'] for x in first['methods']], ['de', 'pso', 'random'])
        for a, b in zip(first['methods'], second['methods']):
            self.assertEqual(a['evaluations'], 8)
            self.assertEqual(a['history'], b['history'])
            self.assertLessEqual(a['history'][-1]['cost'], a['history'][0]['cost'])

    def test_solar_race_obeys_conditions(self):
        result = handle_request('/api/race', {'application': 'solar', 'solar': {'irradiance': 0, 'shade': True}, 'race': {'population': 4, 'generations': 1}})
        self.assertTrue(all(m['history'][-1]['cost'] == 0 for m in result['methods']))
