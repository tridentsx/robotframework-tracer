#!/bin/bash
# Test script to send traces to centralized OTel observability stack

set -e

echo "Testing robotframework-tracer with centralized OTel stack"
echo "=========================================================="

# Test 1: HTTP endpoint
echo ""
echo "Test 1: OTLP HTTP endpoint"
echo "---------------------------"
export OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otel-endpoint.com
export OTEL_SERVICE_NAME=robotframework-tracer-test
export OTEL_EXPORTER_OTLP_INSECURE=true

examples/venv/bin/robot --listener robotframework_tracer.TracingListener \
      --outputdir /tmp/robot_http_test \
      examples/example_test.robot

echo ""
echo "✓ HTTP test completed - check traces at your observability UI"

# Test 2: gRPC endpoint
echo ""
echo "Test 2: OTLP gRPC endpoint"
echo "--------------------------"
export OTEL_EXPORTER_OTLP_ENDPOINT=http://your-otel-grpc-endpoint.com:443
export OTEL_SERVICE_NAME=robotframework-tracer-test-grpc

examples/venv/bin/robot --listener "robotframework_tracer.TracingListener:protocol=grpc" \
      --outputdir /tmp/robot_grpc_test \
      examples/example_test.robot

echo ""
echo "✓ gRPC test completed - check traces at your observability UI"
echo ""
echo "All tests completed successfully!"
