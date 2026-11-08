"""Local JSON API for the React client, backed by the numerical modules."""
import json
import logging
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
from modules.dc_motor import Motor, simulate
from modules.pid_controller import PID
from modules.performance_metrics import calculate_metrics
from modules.differential_evolution import optimize, OptimizationResult
from modules.report_generator import csv_bytes, pdf_bytes
from modules.race import temperature_response, run_race


def inputs(payload):
    motor = Motor(**payload.get('motor', {}))
    pid = PID(**payload.get('pid', {}))
    return motor, pid, float(payload.get('reference', 1000)), float(payload.get('duration', 5))

def serial_response(response):
    return {key: value.tolist() for key, value in response.items()}

def handle_request(path, payload):
    motor, pid, reference, duration = inputs(payload)
    if path == '/api/temperature':
        return {'response': temperature_response(payload.get('temperature', {}), [pid.kp, pid.ki, pid.kd])}
    if path == '/api/race':
        return run_race(payload.get('application', 'motor'), motor, reference, duration, payload.get('settings', {}), payload.get('race', {}), payload.get('solar', {}), payload.get('temperature', {}))
    if path == '/api/simulate':
        response = simulate(motor, pid, reference, duration)
        return {'response': serial_response(response), 'metrics': calculate_metrics(response['time'], response['speed'], reference)}
    if path == '/api/optimize':
        settings = payload.get('settings', {})
        bounds = settings.get('bounds', [[0,1],[0,3],[0,.1]])
        result = optimize(motor, reference, duration, bounds, int(settings.get('popsize',6)), int(settings.get('generations',12)), float(settings.get('mutation',.7)), float(settings.get('crossover',.7)), int(settings.get('seed',42)))
        return asdict(result)
    if path == '/api/csv':
        selected = PID(**payload.get('selected_pid', asdict(pid)))
        return csv_bytes(simulate(motor, selected, reference, duration))
    if path == '/api/report':
        data = payload['optimization']
        result = OptimizationResult(PID(**data['pid']), float(data['fitness']), int(data['generations']), bool(data['success']), str(data['message']), float(data['seconds']), [float(x) for x in data['history']])
        original = simulate(motor, pid, reference, duration)
        tuned = simulate(motor, result.pid, reference, duration)
        return pdf_bytes(motor, pid, result, original, tuned, reference, duration)
    raise ValueError('Unknown API endpoint.')

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length > 1024*1024: raise ValueError('Request is too large.')
            payload = json.loads(self.rfile.read(length) or b'{}')
            result = handle_request(self.path, payload)
            is_bytes = isinstance(result, bytes)
            body = result if is_bytes else json.dumps(result, allow_nan=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', ('application/pdf' if self.path.endswith('report') else 'text/csv') if is_bytes else 'application/json')
        except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError, json.JSONDecodeError) as exc:
            self.send_response(400); self.send_header('Content-Type','application/json'); body=json.dumps({'error':str(exc)}).encode()
        except Exception:
            logging.exception('Unexpected API failure')
            self.send_response(500); self.send_header('Content-Type','application/json'); body=json.dumps({'error':'The server could not complete the request. Check the server log for details.'}).encode()
        self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)

if __name__ == '__main__':
    print('PID API listening on http://127.0.0.1:8000', flush=True)
    ThreadingHTTPServer(('127.0.0.1',8000), Handler).serve_forever()
