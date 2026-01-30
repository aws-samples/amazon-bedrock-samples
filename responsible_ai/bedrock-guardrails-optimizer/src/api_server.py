#!/usr/bin/env python3
"""
Flask API server for the Guardrail Optimization frontend.
Provides REST endpoints for all optimization operations.
"""

import os
import sys
import json
import csv
import io
import glob
import queue
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory, Response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from guardrail_config import get_baseline_config
from guardrail_manager import GuardrailManager
from evaluator import GuardrailEvaluator, TestCase
from generate_test_results import load_csv_inputs, generate_result_files

app = Flask(__name__, static_folder='../static')

# Enable CORS manually to support SSE
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

# Default paths
REPORTS_DIR = "evaluation_reports"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Log queue for streaming logs to frontend
log_queue = queue.Queue()
log_subscribers = []

# Optimization control
optimization_thread = None
optimization_stop_flag = threading.Event()


class LogCapture:
    """Context manager to capture print output and send to log queue."""
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.old_stdout = None
        self.buffer = ""  # Buffer to accumulate partial lines
        
    def __enter__(self):
        self.old_stdout = sys.stdout
        sys.stdout = self
        log_queue.put(f"[{self.operation_name}] Started...")
        return self
        
    def __exit__(self, *args):
        # Flush any remaining buffered content
        if self.buffer.strip():
            log_queue.put(self.buffer.rstrip())
            self.buffer = ""
        sys.stdout = self.old_stdout
        log_queue.put(f"[{self.operation_name}] Completed.")
        
    def write(self, text):
        # Write to original stdout immediately
        if self.old_stdout:
            self.old_stdout.write(text)
        
        # Buffer the text and only send complete lines to the queue
        self.buffer += text
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            if line.strip():
                log_queue.put(line.rstrip())
            
    def flush(self):
        if self.old_stdout:
            self.old_stdout.flush()


def ensure_reports_dir():
    """Ensure reports directory exists."""
    reports_path = os.path.join(PROJECT_ROOT, REPORTS_DIR)
    if not os.path.exists(reports_path):
        os.makedirs(reports_path)
    return reports_path


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory(PROJECT_ROOT, 'index.html')


@app.route('/sample_test_inputs.csv')
def sample_csv():
    """Serve the sample CSV file."""
    return send_from_directory(PROJECT_ROOT, 'sample_test_inputs.csv')


@app.route('/api/logs')
def stream_logs():
    """Stream logs via Server-Sent Events."""
    def generate():
        while True:
            try:
                # Get log message with timeout
                msg = log_queue.get(timeout=1)
                yield f"data: {json.dumps({'message': msg, 'timestamp': datetime.now().isoformat()})}\n\n"
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    })


@app.route('/api/baseline-config', methods=['GET'])
def get_baseline():
    """Get the baseline guardrail configuration."""
    config = get_baseline_config()
    return jsonify(config)


@app.route('/api/evaluate-inputs', methods=['POST'])
def evaluate_inputs():
    """
    Evaluate test inputs against a guardrail and generate passed/failed JSON files.
    
    Expects JSON body with:
    - inputs: list of {input, expected} objects OR csv_content string
    - guardrail_id: optional existing guardrail ID
    - guardrail_config: optional config JSON to deploy
    - region: AWS region (default: us-east-1)
    """
    data = request.json
    region = data.get('region', 'us-east-1')
    
    # Parse inputs from either list or CSV
    test_cases = []
    if 'csv_content' in data:
        reader = csv.DictReader(io.StringIO(data['csv_content']))
        for row in reader:
            expected = row.get('expected', 'pass').strip().lower()
            if expected not in ('pass', 'reject'):
                expected = 'pass'
            test_cases.append(TestCase(input=row['input'].strip(), expected=expected))
    elif 'inputs' in data:
        for item in data['inputs']:
            expected = item.get('expected', 'pass').lower()
            test_cases.append(TestCase(input=item['input'], expected=expected))
    else:
        return jsonify({'error': 'No inputs provided'}), 400
    
    # Get or deploy guardrail
    guardrail_id = data.get('guardrail_id')
    if not guardrail_id:
        config = data.get('guardrail_config') or get_baseline_config()
        if isinstance(config, str):
            config = json.loads(config)
        manager = GuardrailManager(region=region)
        result = manager.create_or_update(config)
        guardrail_id = result['guardrailId']
    
    # Evaluate and generate files
    output_dir = ensure_reports_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with LogCapture("Evaluation"):
        evaluator = GuardrailEvaluator(region=region)
        print(f"Evaluating {len(test_cases)} test cases against guardrail {guardrail_id}...")
        report = evaluator.evaluate_all(guardrail_id, test_cases)
        print(f"Evaluation complete: {report.accuracy*100:.1f}% accuracy")
    
    # Build result files
    passed_results = []
    failed_results = []
    passed_policy_violations = {}
    passed_filter_violations = {}
    failed_false_negatives = 0
    failed_false_positives = 0
    
    for result in report.results:
        entry = {
            "result": "PASSED" if result.passed else "FAILED",
            "input": result.input,
            "expected": result.expected,
            "actual": result.actual,
            "violated_content_filters": result.violated_filters,
            "violated_policies": result.violated_policies
        }
        
        if result.passed:
            passed_results.append(entry)
            for policy in result.violated_policies:
                passed_policy_violations[policy] = passed_policy_violations.get(policy, 0) + 1
            for f in result.violated_filters:
                passed_filter_violations[f] = passed_filter_violations.get(f, 0) + 1
        else:
            failed_results.append(entry)
            if result.expected == "pass" and result.actual == "reject":
                failed_false_positives += 1
            elif result.expected == "reject" and result.actual == "pass":
                failed_false_negatives += 1
    
    # Save files
    passed_file = os.path.join(output_dir, f"passed_guardrail_results_{timestamp}.json")
    failed_file = os.path.join(output_dir, f"failed_guardrail_results_{timestamp}.json")
    
    passed_output = [{"total": len(passed_results), "violated_policies": passed_policy_violations, 
                      "violated_content_filters": passed_filter_violations}] + passed_results
    failed_output = [{"total": f"{len(failed_results)} / {len(passed_results)} (failed / passed)",
                      "false_negatives": f"{failed_false_negatives} (expected to be rejected but passed)",
                      "false_positives": f"{failed_false_positives} (expected to pass but rejected)"}] + failed_results
    
    with open(passed_file, 'w') as f:
        json.dump(passed_output, f, indent=2)
    with open(failed_file, 'w') as f:
        json.dump(failed_output, f, indent=2)
    
    return jsonify({
        'guardrail_id': guardrail_id,
        'passed_file': os.path.basename(passed_file),
        'failed_file': os.path.basename(failed_file),
        'accuracy': report.accuracy,
        'total_tests': report.total_tests,
        'passed_tests': report.passed_tests,
        'failed_tests': report.failed_tests,
        'false_positives': report.false_positives,
        'false_negatives': report.false_negatives
    })


@app.route('/api/run-optimization', methods=['POST'])
def run_optimization_api():
    """
    Start optimization process in a background thread.
    """
    global optimization_thread
    from optimization_agent import run_optimization, _session_state
    
    # Check if optimization is already running
    if optimization_thread and optimization_thread.is_alive():
        return jsonify({'error': 'Optimization already running'}), 400
    
    data = request.json
    passed_file = data.get('passed_file', 'passed_guardrail_results.json')
    failed_file = data.get('failed_file', 'failed_guardrail_results.json')
    
    # Resolve paths relative to project root
    if not os.path.isabs(passed_file):
        passed_file = os.path.join(PROJECT_ROOT, REPORTS_DIR, passed_file) if passed_file.startswith('passed_guardrail_results_') else os.path.join(PROJECT_ROOT, passed_file)
    if not os.path.isabs(failed_file):
        failed_file = os.path.join(PROJECT_ROOT, REPORTS_DIR, failed_file) if failed_file.startswith('failed_guardrail_results_') else os.path.join(PROJECT_ROOT, failed_file)
    
    # Reset stop flag
    optimization_stop_flag.clear()
    
    def run_opt():
        os.chdir(PROJECT_ROOT)
        try:
            with LogCapture("Optimization"):
                run_optimization(
                    max_iterations=data.get('max_iterations', 5),
                    region=data.get('region', 'us-east-1'),
                    start_from_best=not data.get('start_from_baseline', False),
                    target_metrics=data.get('metrics', ['accuracy']),
                    passed_file=passed_file,
                    failed_file=failed_file,
                    stop_flag=optimization_stop_flag
                )
        except Exception as e:
            log_queue.put(f"[Optimization] Error: {str(e)}")
    
    optimization_thread = threading.Thread(target=run_opt, daemon=True)
    optimization_thread.start()
    
    return jsonify({'status': 'started'})


@app.route('/api/stop-optimization', methods=['POST'])
def stop_optimization():
    """Stop the running optimization."""
    global optimization_thread
    
    if not optimization_thread or not optimization_thread.is_alive():
        return jsonify({'error': 'No optimization running'}), 400
    
    optimization_stop_flag.set()
    log_queue.put("[Optimization] Stop requested - will stop after current iteration...")
    
    return jsonify({'status': 'stopping'})


@app.route('/api/optimization-status', methods=['GET'])
def optimization_status():
    """Check if optimization is running."""
    running = optimization_thread is not None and optimization_thread.is_alive()
    return jsonify({'running': running})


@app.route('/api/reports', methods=['GET'])
def list_reports():
    """List all available reports and configs."""
    reports_path = ensure_reports_dir()
    
    files = {
        'evaluations': [],
        'best_configs': [],
        'html_reports': [],
        'pdf_reports': [],
        'passed_files': [],
        'failed_files': []
    }
    
    for f in glob.glob(os.path.join(reports_path, 'eval_*.json')):
        files['evaluations'].append(os.path.basename(f))
    for f in glob.glob(os.path.join(reports_path, 'best_config_*.json')):
        files['best_configs'].append(os.path.basename(f))
    for f in glob.glob(os.path.join(reports_path, '*.html')):
        files['html_reports'].append(os.path.basename(f))
    for f in glob.glob(os.path.join(reports_path, '*.pdf')):
        files['pdf_reports'].append(os.path.basename(f))
    
    # List passed/failed result files from both root and reports dir
    for f in glob.glob(os.path.join(PROJECT_ROOT, 'passed_*.json')):
        files['passed_files'].append(os.path.basename(f))
    for f in glob.glob(os.path.join(reports_path, 'passed_*.json')):
        files['passed_files'].append(os.path.basename(f))
    for f in glob.glob(os.path.join(PROJECT_ROOT, 'failed_*.json')):
        files['failed_files'].append(os.path.basename(f))
    for f in glob.glob(os.path.join(reports_path, 'failed_*.json')):
        files['failed_files'].append(os.path.basename(f))
    
    # Sort by name (which includes timestamp)
    for key in files:
        files[key] = sorted(set(files[key]), reverse=True)
    
    return jsonify(files)


@app.route('/api/reports/<filename>', methods=['GET'])
def get_report(filename):
    """Get a specific report file."""
    reports_path = ensure_reports_dir()
    filepath = os.path.join(reports_path, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    if filename.endswith('.json'):
        with open(filepath, 'r') as f:
            return jsonify(json.load(f))
    else:
        return send_file(filepath)


@app.route('/api/deploy-config', methods=['POST'])
def deploy_config():
    """
    Deploy a guardrail configuration.
    
    Expects JSON body with:
    - config: guardrail configuration object
    - region: AWS region (default: us-east-1)
    """
    data = request.json
    config = data.get('config')
    region = data.get('region', 'us-east-1')
    
    if not config:
        return jsonify({'error': 'No configuration provided'}), 400
    
    if isinstance(config, str):
        config = json.loads(config)
    
    manager = GuardrailManager(region=region)
    with LogCapture("Deploy"):
        print(f"Deploying guardrail configuration...")
        result = manager.create_or_update(config)
        print(f"Deployed guardrail: {result['guardrailId']}")
    
    return jsonify({
        'guardrail_id': result['guardrailId'],
        'version': result['version']
    })


if __name__ == '__main__':
    os.chdir(PROJECT_ROOT)
    # Use reloader_type='stat' to avoid watchdog path issues
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
