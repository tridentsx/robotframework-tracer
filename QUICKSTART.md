# Quick Start Guide

## 1. Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install package
pip install -e .
```

## 2. Start Jaeger

```bash
cd examples
docker-compose up -d
```

**Jaeger is now running on:**
- UI: http://localhost:16686
- OTLP HTTP: http://localhost:14318
- OTLP gRPC: http://localhost:14317

> **Note**: Ports 14318/14317 are used to avoid conflicts with other services.

## 3. Run Example Tests

```bash
# From repository root (with venv activated)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces robot --listener robotframework_tracer.TracingListener examples/example_test.robot
```

**Note**: Use environment variables for configuration. Robot Framework's listener argument parsing has limitations with URLs containing special characters.

## 4. View Traces

1. Open http://localhost:16686
2. Select "robot-framework" from Service dropdown
3. Click "Find Traces"
4. Click on a trace to see details

> **Dark Mode Issue**: Jaeger UI doesn't support dark mode yet. If the UI is unreadable with OS dark mode enabled, use a browser extension like "Dark Reader" and exclude localhost:16686, or temporarily disable OS dark mode.

## 5. Cleanup

```bash
# Stop Jaeger
cd examples
docker-compose down

# Deactivate virtual environment
deactivate
```

## Use with Your Tests

```bash
# Activate venv
source venv/bin/activate

# Set configuration via environment variables
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export OTEL_SERVICE_NAME=my-tests

# Run your tests
robot --listener robotframework_tracer.TracingListener path/to/your/tests/

# View in Jaeger UI
# Open http://localhost:16686 and select "my-tests"
```

## Save Traces to File

```bash
# Auto-generate filename from suite name + trace ID
export RF_TRACER_OUTPUT_FILE=auto
robot --listener robotframework_tracer.TracingListener path/to/your/tests/
# Creates e.g. my_tests_4bf92f35_traces.json

# With minimal filter (~30% smaller output)
export RF_TRACER_OUTPUT_FILE=auto
export RF_TRACER_OUTPUT_FILTER=minimal
robot --listener robotframework_tracer.TracingListener path/to/your/tests/

# Import the file into Jaeger (or any OTLP backend) later
while IFS= read -r line; do
  echo "$line" | curl -s -X POST http://localhost:14318/v1/traces \
    -H "Content-Type: application/json" -d @-
done < my_tests_4bf92f35_traces.json
```

See [docs/configuration.md](docs/configuration.md) for all output options.

## Troubleshooting

### Port conflicts
If you get "port already allocated" errors, the docker-compose already uses alternative ports (14318/14317). If these are also in use, edit `examples/docker-compose.yml` to use different ports.

### No traces appearing
- Verify Jaeger is running: `docker ps | grep jaeger`
- Check the endpoint URL matches: `http://localhost:14318/v1/traces`
- Look for errors in Robot Framework output

### Import errors
```bash
# Reinstall in development mode
pip install -e .
```
