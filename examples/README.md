# Robot Framework Tracer - Examples

This directory contains examples demonstrating how to use robotframework-tracer with Jaeger.

## Quick Start

### 1. Start Jaeger

Start Jaeger using Docker Compose:

```bash
docker-compose up -d
```

This will start Jaeger with:
- **Jaeger UI**: http://localhost:16686
- **OTLP HTTP endpoint**: http://localhost:14318 (mapped from container port 4318)
- **OTLP gRPC endpoint**: http://localhost:14317 (mapped from container port 4317)

> **Note**: Ports 14318 and 14317 are used instead of 4318/4317 to avoid conflicts with other services.

### 2. Install robotframework-tracer

#### Option A: Using virtual environment (recommended)

```bash
# From the repository root
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

#### Option B: System-wide install

```bash
# From the repository root
pip install -e .
```

### 3. Run the example tests

```bash
# Set the endpoint via environment variable
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces

# Run tests
robot --listener robotframework_tracer.TracingListener example_test.robot
```

**Note**: Environment variables are recommended for configuration as Robot Framework's listener argument parsing has limitations with URLs.

### 4. View traces in Jaeger

1. Open http://localhost:16686 in your browser
2. Select "robot-framework" (or your custom service name) from the Service dropdown
3. Click "Find Traces"
4. Click on a trace to see the detailed execution flow

> **Note**: If Jaeger UI is unreadable due to OS dark mode, Jaeger doesn't support dark mode yet. Workarounds:
> - Use a browser extension to force light mode (e.g., "Dark Reader" with site exclusion)
> - Temporarily disable OS dark mode
> - Use browser's reader mode

## What You'll See

The traces will show:
- **Suite span**: The root span for the entire test suite
- **Test spans**: Child spans for each test case
- **Keyword spans**: Nested spans for each keyword execution
- **Attributes**: Test names, tags, status, timing information
- **Error details**: For failed tests, you'll see error messages and events

## Example Trace Structure

```
example_test (suite)
├── Simple Passing Test (test) [PASS]
│   ├── BuiltIn.Log
│   ├── BuiltIn.Should Be Equal
│   └── BuiltIn.Log
├── Test With Multiple Steps (test) [PASS]
│   ├── BuiltIn.Log
│   ├── BuiltIn.Sleep
│   ├── BuiltIn.Log
│   ├── BuiltIn.Should Be True
│   ├── BuiltIn.Log
│   └── BuiltIn.Should Not Be Empty
├── Test With Custom Keyword (test) [PASS]
│   └── My Custom Keyword
│       ├── BuiltIn.Log
│       ├── BuiltIn.Should Not Be Empty
│       └── BuiltIn.Log
└── Failing Test Example (test) [FAIL]
    ├── BuiltIn.Log
    └── BuiltIn.Should Be Equal [FAIL]
```

## Configuration Options

## Configuration Options

### Using Environment Variables (Recommended)

```bash
# Basic configuration
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export OTEL_SERVICE_NAME=my-tests
robot --listener robotframework_tracer.TracingListener example_test.robot
```

### Custom Service Name

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export OTEL_SERVICE_NAME=example-tests
robot --listener robotframework_tracer.TracingListener example_test.robot
```

### Disable Argument Capture

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export RF_TRACER_CAPTURE_ARGUMENTS=false
robot --listener robotframework_tracer.TracingListener example_test.robot
```

### All Configuration Options

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export OTEL_SERVICE_NAME=my-tests
export RF_TRACER_PROTOCOL=http
export RF_TRACER_CAPTURE_ARGUMENTS=true
export RF_TRACER_MAX_ARG_LENGTH=200
export RF_TRACER_CAPTURE_LOGS=false
export RF_TRACER_SAMPLE_RATE=1.0
robot --listener robotframework_tracer.TracingListener example_test.robot
```

## Cleanup

Stop and remove Jaeger:

```bash
docker-compose down
```

## Troubleshooting

### No traces appearing in Jaeger

1. Check that Jaeger is running: `docker ps`
2. Verify the endpoint is correct (example setup: http://localhost:14318/v1/traces)
3. Check Robot Framework output for any tracer errors
4. Ensure the service name matches what you're searching for in Jaeger UI

### Connection errors

If you see connection errors, ensure:
- Jaeger is running and accessible
- The endpoint URL is correct (use port 14318 for the example setup)
- No firewall is blocking the port

### Port conflicts

If you get "port already allocated" errors:
- The example uses ports 14318/14317 to avoid conflicts
- If these are also in use, edit `docker-compose.yml` to use different ports
- Update the endpoint in your robot command accordingly

### Jaeger UI unreadable (dark mode)

Jaeger UI doesn't support dark mode yet. If the UI is unreadable with OS dark mode:
- **Option 1**: Use browser extension "Dark Reader" and exclude `localhost:16686`
- **Option 2**: Temporarily disable OS dark mode
- **Option 3**: Use Firefox/Chrome's built-in reader mode
- **Option 4**: Override with browser DevTools: Press F12, go to Console, run:
  ```javascript
  document.documentElement.style.colorScheme = 'light';
  ```

## Next Steps

- Try modifying the example tests
- Experiment with different configuration options
- Integrate with your own test suites
- Explore the traces in Jaeger UI to understand test execution flow
