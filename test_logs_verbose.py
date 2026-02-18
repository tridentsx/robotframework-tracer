#!/usr/bin/env python3
"""Test with verbose output to see if logs are being sent"""
import os
import sys
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch requests for SSL
import requests
original_request = requests.Session.request

def patched_request(self, *args, **kwargs):
    kwargs['verify'] = False
    # Print what's being sent
    if 'v1/logs' in str(args):
        print(f">>> Sending to logs endpoint: {args[0]} {args[1] if len(args) > 1 else ''}")
    return original_request(self, *args, **kwargs)

requests.Session.request = patched_request

from robot import run

print("Testing logs export to SigNoz")
print("=" * 60)

os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://your-otel-endpoint.com/v1/traces"
os.environ["OTEL_SERVICE_NAME"] = "robotframework-tracer-test"

# Enable Python logging to see OTel errors
import logging
logging.basicConfig(level=logging.DEBUG)

result = run(
    "examples/example_test.robot",
    listener="robotframework_tracer.TracingListener:capture_logs=true:log_level=INFO",
    outputdir="/tmp/robot_logs_test",
    stdout=None,
    stderr=None
)

print("\n" + "=" * 60)
print("Check above for log export attempts")
