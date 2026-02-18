#!/usr/bin/env python3
"""Debug script to verify logs are being sent via Logs API"""
import os
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor, ConsoleLogExporter
from unittest.mock import patch
from robot import run

# Use console exporters to see what's being sent
trace_exporter = ConsoleSpanExporter()
trace_provider = TracerProvider()
trace_provider.add_span_processor(SimpleSpanProcessor(trace_exporter))

log_exporter = ConsoleLogExporter()
log_provider = LoggerProvider()
log_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))

print("Running test with Logs API enabled...")
print("=" * 60)
print("Watch for:")
print("  - Spans (traces)")
print("  - LogRecords (logs) with trace_id and span_id")
print("=" * 60)
print()

# Patch the listener to use our providers
with patch("robotframework_tracer.listener.TracerProvider", return_value=trace_provider):
    with patch("robotframework_tracer.listener.LoggerProvider", return_value=log_provider):
        with patch("robotframework_tracer.listener.trace.set_tracer_provider"):
            with patch("robotframework_tracer.listener.trace.get_tracer") as mock_get_tracer:
                mock_get_tracer.return_value = trace_provider.get_tracer(__name__)
                
                result = run(
                    "examples/example_test.robot",
                    listener="robotframework_tracer.TracingListener:capture_logs=true:log_level=INFO",
                    outputdir="/tmp/robot_logs_debug",
                    stdout=None,
                    stderr=None
                )

print("\n" + "=" * 60)
print("Check above for LogRecord entries with:")
print("  - body: 'Starting simple test', etc.")
print("  - trace_id: (should match span trace_id)")
print("  - span_id: (should match parent span)")
