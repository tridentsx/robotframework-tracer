# Configuration Reference

Complete reference for all configuration options in robotframework-tracer.

## Configuration Methods

### 1. Environment Variables (Recommended)

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export OTEL_SERVICE_NAME=my-tests
export RF_TRACER_SPAN_PREFIX_STYLE=emoji
robot --listener robotframework_tracer.TracingListener tests/
```

### 2. Listener Arguments (Limited)

Due to Robot Framework listener argument parsing limitations with URLs, environment variables are recommended.

## Configuration Options

### Core Options

#### `OTEL_EXPORTER_OTLP_ENDPOINT`
- **Type**: String (URL)
- **Default**: `http://localhost:4318/v1/traces`
- **Description**: OTLP endpoint URL for trace export
- **Example**: `http://jaeger:14318/v1/traces`

#### `OTEL_SERVICE_NAME`
- **Type**: String
- **Default**: `rf`
- **Description**: Service name that appears in traces
- **Example**: `api-tests`, `ui-tests`, `integration-tests`

#### `RF_TRACER_PROTOCOL`
- **Type**: String
- **Default**: `http`
- **Options**: `http`, `grpc`
- **Description**: Protocol for OTLP export
- **Note**: gRPC support in Phase 3

### Span Configuration

#### `RF_TRACER_SPAN_PREFIX_STYLE`
- **Type**: String
- **Default**: `none`
- **Options**: `none`, `text`, `emoji`
- **Description**: Span name prefix style
- **Examples**:
  - `none`: `Example Test`
  - `text`: `[SUITE] Example Test`
  - `emoji`: `📦 Example Test`

**Prefix Mappings:**

| Type | Text | Emoji |
|------|------|-------|
| Suite | `[SUITE]` | 📦 |
| Test Case | `[TEST CASE]` | 🧪 |
| Test Step | `[TEST STEP]` | 👟 |
| Setup | `[SETUP]` | 🔧 |
| Teardown | `[TEARDOWN]` | 🧹 |

### Capture Options

#### `RF_TRACER_CAPTURE_ARGUMENTS`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Capture keyword arguments in spans
- **Example**: `false` to disable

#### `RF_TRACER_MAX_ARG_LENGTH`
- **Type**: Integer
- **Default**: `200`
- **Description**: Maximum length for captured arguments
- **Example**: `500` for longer arguments

#### `RF_TRACER_CAPTURE_LOGS`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Capture log messages via OpenTelemetry Logs API
- **Note**: Logs are sent to `/v1/logs` endpoint with trace correlation

### Sampling

#### `RF_TRACER_SAMPLE_RATE`
- **Type**: Float (0.0-1.0)
- **Default**: `1.0`
- **Description**: Sampling rate for traces
- **Examples**:
  - `1.0`: Capture all traces (100%)
  - `0.5`: Capture 50% of traces
  - `0.1`: Capture 10% of traces

### Parent Trace Context

#### `TRACEPARENT`
- **Type**: String (W3C Trace Context format)
- **Default**: Not set
- **Description**: When set, the suite span becomes a child of the specified parent trace. Follows the [W3C Trace Context](https://www.w3.org/TR/trace-context/) standard.
- **Example**: `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`
- **Use case**: CI/CD correlation, pabot parallel execution

#### `TRACESTATE`
- **Type**: String
- **Default**: Not set
- **Description**: Optional vendor-specific trace state, used alongside `TRACEPARENT`.
- **Example**: `vendor1=value1,vendor2=value2`

### Trace Output File

#### `RF_TRACER_OUTPUT_FILE`
- **Type**: String
- **Default**: `` (disabled)
- **Options**: `auto`, or an explicit file path
- **Description**: Write spans as JSON to a local file (in addition to OTLP export). Overwrites on each run.
- **Examples**:
  - `auto`: Auto-generates filename from suite name and trace ID, e.g. `diverse_suite_4bf92f35_traces.json`
  - `traces.json`: Always writes to `traces.json`

#### `RF_TRACER_OUTPUT_FORMAT`
- **Type**: String
- **Default**: `json`
- **Options**: `json`, `gz`
- **Description**: Output format for the trace file. `gz` writes gzip-compressed output (streaming), typically ~90% smaller.
- **Examples**:
  - `json`: OTLP-compatible JSON (one batch per line)
  - `gz`: Gzip-compressed OTLP JSON (e.g. `diverse_suite_4bf92f35_traces.json.gz`)

#### `RF_TRACER_OUTPUT_FILTER`
- **Type**: String
- **Default**: `` (disabled — full output)
- **Options**: Built-in preset name (`minimal`, `full`) or path to a custom filter `.json` file
- **Description**: Apply a filter to reduce the size of trace output files. The filter controls which resource attributes, span types, span fields, span attributes, and events are included. The filter file is validated against a JSON Schema (`schemas/output-filter-v1.json`) on load — invalid configs are rejected with warnings.
- **Examples**:
  - `minimal`: Built-in preset that strips events, timing attributes, and IDs (~30% smaller)
  - `full`: Built-in preset that includes everything (same as no filter, useful as a template)
  - `./my-filter.json`: Custom filter file

**Built-in presets:**

| Preset | Description |
|--------|-------------|
| `full` | All spans, attributes, and events included (empty arrays = include all) |
| `minimal` | Reduced attributes, no events, no flags/kind fields |

**Custom filter example:**

```json
{
  "version": "1.0.0",
  "description": "My custom filter",
  "resource": {
    "include_attributes": true,
    "attribute_keys": ["service.name", "rf.version"]
  },
  "spans": {
    "include_suites": true,
    "include_tests": true,
    "include_keywords": true,
    "keyword_types": [],
    "max_depth": null,
    "fields": [],
    "attributes": {
      "include": [],
      "exclude": ["rf.keyword.args", "rf.elapsed_time"]
    },
    "include_events": false
  },
  "scope": {
    "include": true
  }
}
```

Empty arrays `[]` and `null` mean "include everything" (no filtering). See `src/robotframework_tracer/presets/full.json` for all configurable options.

## Configuration Examples

### Basic Setup

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
robot --listener robotframework_tracer.TracingListener tests/
```

### Custom Service Name

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export OTEL_SERVICE_NAME=api-integration-tests
robot --listener robotframework_tracer.TracingListener tests/
```

### With Emoji Prefixes

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export RF_TRACER_SPAN_PREFIX_STYLE=emoji
robot --listener robotframework_tracer.TracingListener tests/
```

### Disable Argument Capture

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export RF_TRACER_CAPTURE_ARGUMENTS=false
robot --listener robotframework_tracer.TracingListener tests/
```

### With Sampling

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export RF_TRACER_SAMPLE_RATE=0.1  # Sample 10% of traces
robot --listener robotframework_tracer.TracingListener tests/
```

### With Trace Output File

```bash
# Auto-generate filename from suite name + trace ID
export RF_TRACER_OUTPUT_FILE=auto
robot --listener robotframework_tracer.TracingListener tests/
# Creates e.g. diverse_suite_4bf92f35_traces.json

# Gzip-compressed (streaming, ~90% smaller)
export RF_TRACER_OUTPUT_FILE=auto
export RF_TRACER_OUTPUT_FORMAT=gz
robot --listener robotframework_tracer.TracingListener tests/
# Creates e.g. diverse_suite_4bf92f35_traces.json.gz

# With output filter (reduce file size ~30%)
export RF_TRACER_OUTPUT_FILE=auto
export RF_TRACER_OUTPUT_FILTER=minimal
robot --listener robotframework_tracer.TracingListener tests/

# Or use a fixed filename (overwritten each run)
export RF_TRACER_OUTPUT_FILE=traces.json
robot --listener robotframework_tracer.TracingListener tests/
```

#### Importing trace files into a backend

The output file is standard OTLP JSON (NDJSON format — one `ExportTraceServiceRequest` per line). Import it into any OTLP-compatible backend by POSTing each line to the OTLP HTTP endpoint:

```bash
# Import into Jaeger (or any OTLP HTTP endpoint)
while IFS= read -r line; do
  echo "$line" | curl -s -X POST http://localhost:4318/v1/traces \
    -H "Content-Type: application/json" -d @-
done < diverse_suite_4bf92f35_traces.json
```

> **Note:** Jaeger UI's "Upload JSON" button expects Jaeger's own JSON format and cannot import OTLP JSON directly. Use the OTLP HTTP endpoint instead.

### Complete Configuration

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export OTEL_SERVICE_NAME=my-tests
export RF_TRACER_PROTOCOL=http
export RF_TRACER_SPAN_PREFIX_STYLE=emoji
export RF_TRACER_CAPTURE_ARGUMENTS=true
export RF_TRACER_MAX_ARG_LENGTH=200
export RF_TRACER_CAPTURE_LOGS=false
export RF_TRACER_SAMPLE_RATE=1.0
export RF_TRACER_OUTPUT_FILE=auto
export RF_TRACER_OUTPUT_FORMAT=json
export RF_TRACER_OUTPUT_FILTER=minimal

robot --listener robotframework_tracer.TracingListener tests/
```

## Backend-Specific Configuration

### Jaeger

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318/v1/traces
export OTEL_SERVICE_NAME=my-tests
```

### Grafana Tempo

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318/v1/traces
export OTEL_SERVICE_NAME=my-tests
```

### Zipkin

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://zipkin:9411/api/v2/spans
export OTEL_SERVICE_NAME=my-tests
```

## Configuration Precedence

1. **Environment Variables** (highest priority)
2. **Default Values** (lowest priority)

## Best Practices

### 1. Use Descriptive Service Names
```bash
# Good
export OTEL_SERVICE_NAME=api-integration-tests
export OTEL_SERVICE_NAME=ui-smoke-tests

# Avoid
export OTEL_SERVICE_NAME=tests
export OTEL_SERVICE_NAME=rf
```

### 2. Use Emoji Prefixes for Better Visibility
```bash
export RF_TRACER_SPAN_PREFIX_STYLE=emoji
```

### 3. Adjust Argument Length for Your Needs
```bash
# For tests with long arguments
export RF_TRACER_MAX_ARG_LENGTH=500

# For tests with sensitive data
export RF_TRACER_CAPTURE_ARGUMENTS=false
```

### 4. Use Sampling for Large Test Suites
```bash
# Sample 10% in development
export RF_TRACER_SAMPLE_RATE=0.1

# Sample 100% in CI/CD
export RF_TRACER_SAMPLE_RATE=1.0
```

## Troubleshooting

### Traces Not Appearing

1. Check endpoint URL is correct
2. Verify backend is running
3. Check for errors in Robot Framework output
4. Verify service name matches in Jaeger UI

### Connection Errors

1. Ensure endpoint is accessible
2. Check firewall rules
3. Verify port is correct (14318 for example setup)

### Performance Issues

1. Reduce `RF_TRACER_MAX_ARG_LENGTH`
2. Set `RF_TRACER_CAPTURE_ARGUMENTS=false`
3. Increase `RF_TRACER_SAMPLE_RATE` to sample fewer traces

## Future Configuration Options (Phase 3+)

- Authentication headers
- TLS/SSL configuration
- Export timeout
- Log level filtering
- Configuration file support (.rf-tracer.yml)

## See Also

- [Attribute Reference](attributes.md)
- [Backend Setup](backends.md)
- [Quick Start Guide](../QUICKSTART.md)
