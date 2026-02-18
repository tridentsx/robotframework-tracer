# Centralized OTel Stack Testing

This directory contains tests configured to send traces to the centralized OpenTelemetry observability stack at Ericsson.

## Endpoints

**OTLP HTTP (HTTPS):**
```
https://otel.hall035.rnd.gic.ericsson.se/v1/traces
```

**OTLP gRPC:**
```
otel-grpc.hall035.rnd.gic.ericsson.se:80 (insecure)
```

## Running Tests

### Quick Test
```bash
# Run with Python (handles SSL self-signed cert automatically)
# Includes log capture at INFO level
examples/venv/bin/python3 test_centralized_otel.py
```

### Manual Test with Robot
```bash
# Set environment variables
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.hall035.rnd.gic.ericsson.se/v1/traces
export OTEL_SERVICE_NAME=my-robot-tests

# Run tests with log capture
robot --listener "robotframework_tracer.TracingListener:capture_logs=true:log_level=INFO" examples/example_test.robot
```

## Notes

- The HTTPS endpoint uses a self-signed certificate
- The test script (`test_centralized_otel.py`) automatically handles SSL verification
- **Log capture is ENABLED** - Robot Framework logs are sent via OpenTelemetry Logs API
- Log level set to INFO (captures INFO, WARN, ERROR, FAIL)
- Logs are sent to `/v1/logs` endpoint with full trace correlation
- For manual testing, you may need to configure SSL verification in your environment
- Traces are sent with service name `robotframework-tracer-test`

### Log Capture Configuration:
- `capture_logs=true` - Enables log capture via Logs API
- `log_level=INFO` - Minimum log level (DEBUG, INFO, WARN, ERROR)
- `max_log_length=500` - Maximum characters per log message (default)
- Logs include `trace_id` and `span_id` for correlation

## Expected Results

The test suite creates:
- **Traces** (sent to `/v1/traces`):
  - 1 suite span (Example Test)
  - 4 test case spans
  - Multiple keyword spans (including nested keywords)
  - One test intentionally fails to demonstrate failure tracing

- **Logs** (sent to `/v1/logs`):
  - 12+ log records correlated to traces
  - Each log includes trace_id and span_id for correlation
  - Logs appear in SigNoz Logs UI with full trace context

- **Metrics** (sent to `/v1/metrics`):
  - `rf.tests.total`: 4
  - `rf.tests.passed`: 3
  - `rf.tests.failed`: 1
  - `rf.test.duration`: histogram of test execution times
  - `rf.suite.duration`: suite execution time
  - `rf.keywords.executed`: total keywords executed
  - `rf.keyword.duration`: histogram of keyword execution times

### Log Events Captured:
- "Starting simple test"
- "Test completed successfully"
- "Step 1: Initialize", "Step 2: Execute", "Step 3: Verify"
- "Custom keyword called with: Hello World"
- "Custom keyword completed"
- "This test demonstrates failure tracing"

**Check SigNoz:**
- **Traces UI**: View execution flow and timing
- **Logs UI**: View log messages with trace correlation
- **Metrics UI**: View test execution metrics and trends
- Click on a log → Jump to its trace
- Click on a trace → See related logs
- View metrics dashboards for test health over time

## Test Output

Test results are saved to `/tmp/robot_https_test/`:
- `output.xml` - Robot Framework test results
- `log.html` - Detailed test log
- `report.html` - Test report

## Troubleshooting

**Connection timeout:**
- Verify you're on the correct network
- Check firewall rules
- Ensure port 443 is accessible

**SSL certificate errors:**
- Use the provided Python script which handles self-signed certs
- Or configure your environment to trust the certificate

**404 errors:**
- Ensure the full path `/v1/traces` is included in the endpoint URL
