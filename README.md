# Robot Framework Tracer

OpenTelemetry distributed tracing integration for Robot Framework test execution.

## What is this?

`robotframework-tracer` is a Robot Framework listener plugin that automatically creates distributed traces for your test execution using OpenTelemetry. It captures the complete test hierarchy (suites → tests → keywords) as spans and exports them to any OpenTelemetry-compatible backend like Jaeger, Grafana Tempo, or Zipkin.

This enables you to:
- **Visualize test execution flow** with detailed timing information
- **Debug test failures** by examining the complete execution trace
- **Analyze performance** and identify slow keywords or tests
- **Correlate tests with application traces** in distributed systems
- **Monitor test execution** across CI/CD pipelines

![Robot Framework Trace Visualization](docs/robotframework-trace.jpg)

## How it works

The tracer implements the Robot Framework Listener v3 API and creates OpenTelemetry spans for each test execution phase:

```
Suite Span (root)
├── Test Case Span
│   ├── Keyword Span
│   │   └── Nested Keyword Span
│   └── Keyword Span
└── Test Case Span
    └── Keyword Span
```

Each span includes rich metadata: test names, tags, status (PASS/FAIL), timing, arguments, and error details.

## Installation

### From PyPI (when released)

```bash
pip install robotframework-tracer
```

### From Source (Development)

```bash
# Clone the repository
git clone <repository-url>
cd robotframework-tracer

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development setup instructions.

## Quick Start

### 1. Start a tracing backend (Jaeger example)

```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest
```

### 2. Run your tests with the listener

```bash
robot --listener robotframework_tracer.TracingListener tests/
```

### 3. View traces

Open http://localhost:16686 in your browser to see your test traces in Jaeger UI.

## Configuration

### Basic usage

```bash
robot --listener robotframework_tracer.TracingListener tests/
```

### Custom endpoint

```bash
robot --listener robotframework_tracer.TracingListener:endpoint=http://jaeger:4318/v1/traces tests/
```

### Custom service name

```bash
robot --listener "robotframework_tracer.TracingListener:endpoint=http://jaeger:4318/v1/traces,service_name=my-tests" tests/
```

### All configuration options

```bash
robot --listener "robotframework_tracer.TracingListener:\
endpoint=http://localhost:4318/v1/traces,\
service_name=robot-tests,\
protocol=http,\
capture_arguments=true,\
max_arg_length=200" tests/
```

### Environment variables

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_SERVICE_NAME=robot-framework-tests
robot --listener robotframework_tracer.TracingListener tests/
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `endpoint` | `http://localhost:4318/v1/traces` | OTLP endpoint URL |
| `service_name` | `rf` | Service name in traces |
| `protocol` | `http` | Protocol: `http` or `grpc` |
| `span_prefix_style` | `none` | Span prefix style: `none`, `text`, `emoji` |
| `capture_arguments` | `true` | Capture keyword arguments |
| `max_arg_length` | `200` | Max length for arguments |
| `capture_logs` | `false` | Capture log messages as events |
| `log_level` | `INFO` | Minimum log level (DEBUG, INFO, WARN, ERROR) |
| `max_log_length` | `500` | Max length for log messages |
| `sample_rate` | `1.0` | Sampling rate (0.0-1.0, 1.0 = no sampling) |

## Span Attributes

Each span includes relevant Robot Framework metadata:

**Suite spans:**
- `rf.suite.name` - Suite name
- `rf.suite.source` - Suite file path
- `rf.suite.id` - Suite ID
- `rf.version` - Robot Framework version

**Test spans:**
- `rf.test.name` - Test case name
- `rf.test.id` - Test ID
- `rf.test.tags` - Test tags
- `rf.status` - PASS/FAIL/SKIP
- `rf.elapsed_time` - Execution time

**Keyword spans:**
- `rf.keyword.name` - Keyword name
- `rf.keyword.type` - SETUP/TEARDOWN/KEYWORD
- `rf.keyword.library` - Library name
- `rf.keyword.args` - Arguments (if enabled)
- `rf.status` - PASS/FAIL

## Supported Backends

Works with any OpenTelemetry-compatible backend:
- **Jaeger** - Open source tracing platform
- **Grafana Tempo** - High-scale distributed tracing
- **Zipkin** - Distributed tracing system
- **AWS X-Ray** - AWS distributed tracing
- **Honeycomb** - Observability platform
- **Datadog** - Monitoring and analytics

See [docs/backends.md](docs/backends.md) for backend-specific setup guides.

## Requirements

- Python 3.8+
- Robot Framework 6.0+
- OpenTelemetry SDK

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Design and architecture details
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Development roadmap
- [Configuration Guide](docs/configuration.md) - Detailed configuration reference
- [Attribute Reference](docs/attributes.md) - Complete attribute documentation
- [Backend Setup](docs/backends.md) - Backend-specific guides

## Examples

See the [examples/](examples/) directory for complete examples:
- Basic usage with Jaeger
- Advanced configuration
- CI/CD integration
- Multiple backend setups

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Status

**Current Version:** v0.1.0  
**Status:** Production-ready MVP

Core functionality is complete and tested. See [CHANGELOG.md](CHANGELOG.md) for version history and [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the development roadmap.
