#!/bin/bash
# Test script to send traces to centralized OTel observability stack

set -e

echo "Testing robotframework-tracer with centralized OTel stack"
echo "=========================================================="

# Test 1: HTTP endpoint
echo ""
echo "Test 1: OTLP HTTP endpoint"
echo "---------------------------"
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.hall035.rnd.gic.ericsson.se
export OTEL_SERVICE_NAME=robotframework-tracer-test
export OTEL_EXPORTER_OTLP_INSECURE=true

examples/venv/bin/robot --listener robotframework_tracer.TracingListener \
      --outputdir /tmp/robot_http_test \
      examples/example_test.robot

echo ""
echo "✓ HTTP test completed - check traces at http://otel.hall035.rnd.gic.ericsson.se"

# Test 2: gRPC endpoint
echo ""
echo "Test 2: OTLP gRPC endpoint"
echo "--------------------------"
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-grpc.hall035.rnd.gic.ericsson.se:80
export OTEL_SERVICE_NAME=robotframework-tracer-test-grpc

examples/venv/bin/robot --listener "robotframework_tracer.TracingListener:protocol=grpc" \
      --outputdir /tmp/robot_grpc_test \
      examples/example_test.robot

echo ""
echo "✓ gRPC test completed - check traces at your observability UI"
echo ""
echo "All tests completed successfully!"
