#!/usr/bin/env python3
"""
Test script to send traces to centralized OTel observability stack at Ericsson.

This script runs Robot Framework tests with the tracer listener and sends
traces to the centralized OTLP endpoint. It handles SSL verification for
self-signed certificates.

Endpoints tested:
- HTTPS: https://otel.hall035.rnd.gic.ericsson.se/v1/traces
"""
import os
import sys
import urllib3

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Monkey patch requests to disable SSL verification for self-signed certs
import requests
original_request = requests.Session.request

def patched_request(self, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, *args, **kwargs)

requests.Session.request = patched_request

# Now run robot
from robot import run

print("Testing robotframework-tracer with centralized OTel stack")
print("=" * 60)

# Test: HTTPS endpoint
print("\nTest: OTLP HTTPS endpoint with log capture")
print("-" * 30)
print("Endpoint: https://otel.hall035.rnd.gic.ericsson.se/v1/traces")
print("Service:  robotframework-tracer-test")
print("Logs:     ENABLED (level: INFO)")
print()

os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://otel.hall035.rnd.gic.ericsson.se/v1/traces"
os.environ["OTEL_SERVICE_NAME"] = "robotframework-tracer-test"

result = run(
    "examples/example_test.robot",
    listener="robotframework_tracer.TracingListener:capture_logs=true:log_level=INFO",
    outputdir="/tmp/robot_https_test",
    stdout=None,
    stderr=None
)

print(f"\n✓ Test completed (exit code: {result})")
print("  Traces sent to:  https://otel.hall035.rnd.gic.ericsson.se/v1/traces")
print("  Logs sent to:    https://otel.hall035.rnd.gic.ericsson.se/v1/logs")
print("  Metrics sent to: https://otel.hall035.rnd.gic.ericsson.se/v1/metrics")
print("  Service name: robotframework-tracer-test")
print("\nCheck your observability UI for the traces!")
print("\nExpected spans:")
print("  - 1 suite span (Example Test)")
print("  - 4 test spans (Simple Passing Test, Test With Multiple Steps, etc.)")
print("  - Multiple keyword spans")
print("\nExpected log events (in SigNoz Logs UI):")
print("  - 'Starting simple test'")
print("  - 'Test completed successfully'")
print("  - 'Step 1: Initialize', 'Step 2: Execute', 'Step 3: Verify'")
print("  - 'Custom keyword called with: Hello World'")
print("  - 'This test demonstrates failure tracing'")
print("  - And more...")
print("\nExpected metrics (in SigNoz Metrics UI):")
print("  - rf.tests.total: 4 (3 passed, 1 failed)")
print("  - rf.tests.passed: 3")
print("  - rf.tests.failed: 1")
print("  - rf.test.duration: histogram of test execution times")
print("  - rf.suite.duration: suite execution time")
print("  - rf.keywords.executed: total keywords executed")
print("  - rf.keyword.duration: histogram of keyword execution times")
print("\nLogs are correlated to traces via trace_id and span_id!")

