#!/usr/bin/env python3
"""Debug script to verify log capture is working"""
import os
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from unittest.mock import patch
from robot import run

# Use console exporter to see what's being sent
exporter = ConsoleSpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))

# Patch the listener to use our provider
with patch("robotframework_tracer.listener.TracerProvider", return_value=provider):
    with patch("robotframework_tracer.listener.trace.set_tracer_provider"):
        with patch("robotframework_tracer.listener.trace.get_tracer") as mock_get_tracer:
            mock_get_tracer.return_value = provider.get_tracer(__name__)
            
            print("Running test with log capture enabled...")
            print("=" * 60)
            
            result = run(
                "examples/example_test.robot",
                listener="robotframework_tracer.TracingListener:capture_logs=true:log_level=INFO",
                outputdir="/tmp/robot_debug_test",
                stdout=None,
                stderr=None
            )

print("\n" + "=" * 60)
print("Check the output above for 'events' in the span data")
print("Events should contain log messages like 'Starting simple test'")
