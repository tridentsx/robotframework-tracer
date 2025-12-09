# Robot Framework Distributed Tracer - Architecture & Implementation Plan

## Project Overview

**Name**: `robotframework-tracer`  
**Purpose**: OpenTelemetry distributed tracing integration for Robot Framework test execution  
**Type**: External Robot Framework Listener Plugin  
**License**: Apache 2.0 (compatible with Robot Framework)

## Architecture

### High-Level Design

```
Robot Framework Test Execution
         ↓
    Listener API (hooks)
         ↓
  robotframework-tracer
         ↓
   OpenTelemetry SDK
         ↓
  OTLP Exporter (gRPC/HTTP)
         ↓
  Tracing Backend (Jaeger/Tempo/etc)
```

### Span Hierarchy

```
Suite Span (root)
├── attributes: suite.name, suite.source, suite.metadata, tags
├── baggage: rf.version, rf.suite.id
│
├─── Test Case Span
│    ├── attributes: test.name, test.tags, test.template
│    ├── status: PASS/FAIL
│    ├── events: test setup/teardown
│    │
│    ├─── Keyword Span (test step)
│    │    ├── attributes: keyword.name, keyword.type, keyword.args
│    │    ├── status: PASS/FAIL
│    │    └── events: log messages (optional)
│    │
│    └─── Keyword Span (nested)
│
└─── Suite Teardown Span (if exists)
```

## Repository Structure

```
robotframework-tracer/
├── README.md
├── LICENSE
├── setup.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
├── CONTRIBUTING.md
├── ARCHITECTURE.md (this file)
│
├── src/
│   └── robotframework_tracer/
│       ├── __init__.py
│       ├── listener.py           # Main listener implementation
│       ├── span_builder.py       # Span creation logic
│       ├── config.py             # Configuration management
│       ├── attributes.py         # Attribute mapping/extraction
│       └── version.py
│
├── tests/
│   ├── unit/
│   │   ├── test_listener.py
│   │   ├── test_span_builder.py
│   │   └── test_config.py
│   └── integration/
│       ├── test_suites/
│       │   ├── simple.robot
│       │   └── nested.robot
│       └── test_integration.py
│
├── examples/
│   ├── docker-compose.yml        # Jaeger + example setup
│   ├── simple_test.robot
│   └── README.md
│
└── docs/
    ├── configuration.md
    ├── attributes.md
    └── backends.md
```

## Core Components

### 1. Listener (`listener.py`)

**Responsibility**: Implement Robot Framework Listener v3 API

```python
class TracingListener:
    """
    Robot Framework Listener v3 that creates distributed traces.
    
    Usage:
        robot --listener robotframework_tracer.TracingListener:endpoint=http://localhost:4318 tests/
    """
    
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self, endpoint=None, service_name="robot-framework", **kwargs):
        # Initialize OpenTelemetry tracer
        pass
    
    # Suite lifecycle
    def start_suite(self, data, result):
        # Create root span for suite
        pass
    
    def end_suite(self, data, result):
        # Close suite span with final status
        pass
    
    # Test lifecycle
    def start_test(self, data, result):
        # Create child span for test case
        pass
    
    def end_test(self, data, result):
        # Close test span with verdict (PASS/FAIL)
        pass
    
    # Keyword lifecycle
    def start_keyword(self, data, result):
        # Create child span for keyword/step
        pass
    
    def end_keyword(self, data, result):
        # Close keyword span with status
        pass
    
    # Optional: capture log messages as events
    def log_message(self, message):
        # Add span event for important logs
        pass
```

### 2. Span Builder (`span_builder.py`)

**Responsibility**: Create and configure spans with proper attributes

```python
class SpanBuilder:
    """Builds OpenTelemetry spans from Robot Framework objects."""
    
    def create_suite_span(self, suite_data, suite_result):
        """Create root span for test suite."""
        # Extract: name, source, metadata, tags
        # Set baggage: rf.version, suite.id
        pass
    
    def create_test_span(self, test_data, test_result, parent_span):
        """Create child span for test case."""
        # Extract: name, tags, template, timeout
        pass
    
    def create_keyword_span(self, kw_data, kw_result, parent_span):
        """Create child span for keyword/step."""
        # Extract: name, type, library, args
        pass
    
    def set_span_status(self, span, result):
        """Set span status based on RF result (PASS/FAIL/SKIP)."""
        pass
    
    def add_error_event(self, span, result):
        """Add error event with exception details."""
        pass
```

### 3. Configuration (`config.py`)

**Responsibility**: Parse and validate configuration options

```python
class TracerConfig:
    """Configuration for the tracing listener."""
    
    def __init__(self, **kwargs):
        self.endpoint = kwargs.get('endpoint', 'http://localhost:4318')
        self.service_name = kwargs.get('service_name', 'robot-framework')
        self.protocol = kwargs.get('protocol', 'http')  # http or grpc
        self.headers = self._parse_headers(kwargs.get('headers', ''))
        self.sample_rate = float(kwargs.get('sample_rate', 1.0))
        self.capture_logs = kwargs.get('capture_logs', 'false').lower() == 'true'
        self.capture_arguments = kwargs.get('capture_arguments', 'true').lower() == 'true'
        self.max_arg_length = int(kwargs.get('max_arg_length', 200))
    
    @staticmethod
    def from_listener_args(args_string):
        """Parse listener arguments from command line."""
        pass
```

### 4. Attributes (`attributes.py`)

**Responsibility**: Define semantic conventions for RF attributes

```python
# Semantic conventions for Robot Framework traces
class RFAttributes:
    """OpenTelemetry semantic conventions for Robot Framework."""
    
    # Suite attributes
    SUITE_NAME = "rf.suite.name"
    SUITE_SOURCE = "rf.suite.source"
    SUITE_ID = "rf.suite.id"
    SUITE_METADATA = "rf.suite.metadata"
    
    # Test attributes
    TEST_NAME = "rf.test.name"
    TEST_ID = "rf.test.id"
    TEST_TAGS = "rf.test.tags"
    TEST_TEMPLATE = "rf.test.template"
    TEST_TIMEOUT = "rf.test.timeout"
    
    # Keyword attributes
    KEYWORD_NAME = "rf.keyword.name"
    KEYWORD_TYPE = "rf.keyword.type"  # SETUP, TEARDOWN, KEYWORD
    KEYWORD_LIBRARY = "rf.keyword.library"
    KEYWORD_ARGS = "rf.keyword.args"
    KEYWORD_ASSIGN = "rf.keyword.assign"
    
    # Result attributes
    STATUS = "rf.status"  # PASS, FAIL, SKIP, NOT_RUN
    MESSAGE = "rf.message"
    START_TIME = "rf.start_time"
    END_TIME = "rf.end_time"
    ELAPSED_TIME = "rf.elapsed_time"
    
    # Framework attributes
    RF_VERSION = "rf.version"
    PYTHON_VERSION = "rf.python.version"

class AttributeExtractor:
    """Extract attributes from Robot Framework objects."""
    
    @staticmethod
    def from_suite(suite_data, suite_result):
        """Extract attributes from suite."""
        pass
    
    @staticmethod
    def from_test(test_data, test_result):
        """Extract attributes from test."""
        pass
    
    @staticmethod
    def from_keyword(kw_data, kw_result):
        """Extract attributes from keyword."""
        pass
```

## Implementation Phases

### Phase 1: MVP (Minimum Viable Product)
**Goal**: Basic tracing with suite → test → keyword hierarchy

- [ ] Project setup (repo, dependencies, CI)
- [ ] Implement basic listener with suite/test/keyword hooks
- [ ] Create spans with minimal attributes (name, status)
- [ ] OTLP HTTP exporter to Jaeger
- [ ] Basic unit tests
- [ ] Docker Compose example with Jaeger
- [ ] README with usage instructions

**Deliverable**: Can trace a simple test suite to Jaeger

### Phase 2: Rich Attributes
**Goal**: Add comprehensive metadata and baggage

- [ ] Implement full attribute extraction
- [ ] Add baggage propagation (suite metadata)
- [ ] Add tags as span attributes
- [ ] Add test/keyword arguments (with size limits)
- [ ] Add timing information
- [ ] Configuration options for attribute filtering

**Deliverable**: Traces contain all relevant RF metadata

### Phase 3: Advanced Features
**Goal**: Production-ready features

- [ ] Log message capture as span events
- [ ] Error/exception details in span events
- [ ] Sampling configuration
- [ ] gRPC exporter support
- [ ] Environment variable configuration
- [ ] Multiple backend support (Jaeger, Tempo, Zipkin)
- [ ] Performance optimization (async export)

**Deliverable**: Production-ready plugin

### Phase 4: Ecosystem Integration
**Goal**: Integration with common RF patterns

- [ ] Support for parallel execution (pabot)
- [ ] Support for remote execution
- [ ] Integration with RF metrics
- [ ] Custom span processors
- [ ] Trace context injection for HTTP libraries
- [ ] Documentation and examples

**Deliverable**: Works with real-world RF setups

## Dependencies

### Core Dependencies
```
robotframework>=6.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-otlp-proto-http>=1.20.0
opentelemetry-exporter-otlp-proto-grpc>=1.20.0  # optional
```

### Development Dependencies
```
pytest>=7.0
pytest-cov
black
ruff
mypy
```

## Configuration Options

### Command Line Usage

```bash
# Basic usage
robot --listener robotframework_tracer.TracingListener tests/

# With endpoint
robot --listener robotframework_tracer.TracingListener:endpoint=http://jaeger:4318 tests/

# Full configuration
robot --listener "robotframework_tracer.TracingListener:endpoint=http://jaeger:4318,service_name=my-tests,capture_logs=true" tests/
```

### Environment Variables

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_SERVICE_NAME=robot-framework-tests
export RF_TRACER_CAPTURE_LOGS=true
export RF_TRACER_SAMPLE_RATE=1.0
```

### Configuration File (future)

```yaml
# .rf-tracer.yml
endpoint: http://localhost:4318
service_name: robot-framework-tests
protocol: http
capture_logs: true
capture_arguments: true
max_arg_length: 200
sample_rate: 1.0
```

## Span Attribute Examples

### Suite Span
```json
{
  "name": "My Test Suite",
  "kind": "INTERNAL",
  "attributes": {
    "rf.suite.name": "My Test Suite",
    "rf.suite.source": "/path/to/suite.robot",
    "rf.suite.id": "s1",
    "rf.version": "7.0.0",
    "rf.python.version": "3.11.0",
    "rf.suite.metadata.author": "John Doe",
    "rf.suite.metadata.version": "1.0"
  },
  "baggage": {
    "rf.suite.id": "s1",
    "rf.version": "7.0.0"
  }
}
```

### Test Span
```json
{
  "name": "Login Test",
  "kind": "INTERNAL",
  "attributes": {
    "rf.test.name": "Login Test",
    "rf.test.id": "s1-t1",
    "rf.test.tags": ["smoke", "login"],
    "rf.status": "PASS",
    "rf.elapsed_time": "2.345"
  }
}
```

### Keyword Span
```json
{
  "name": "Input Text",
  "kind": "INTERNAL",
  "attributes": {
    "rf.keyword.name": "Input Text",
    "rf.keyword.type": "KEYWORD",
    "rf.keyword.library": "SeleniumLibrary",
    "rf.keyword.args": ["id=username", "admin"],
    "rf.status": "PASS"
  }
}
```

## Testing Strategy

### Unit Tests
- Test listener initialization
- Test span creation logic
- Test attribute extraction
- Test configuration parsing
- Mock OpenTelemetry SDK

### Integration Tests
- Run actual Robot Framework tests with listener
- Verify span hierarchy
- Verify attributes
- Test with in-memory exporter

### End-to-End Tests
- Docker Compose with Jaeger
- Run test suite
- Query Jaeger API to verify traces
- Verify span relationships

## Performance Considerations

1. **Async Export**: Use batch span processor to avoid blocking test execution
2. **Sampling**: Support configurable sampling for large test suites
3. **Attribute Limits**: Limit argument/log message sizes
4. **Memory**: Clean up span references after export
5. **Overhead**: Target <5% overhead on test execution time

## Security Considerations

1. **Sensitive Data**: Option to disable argument capture
2. **Credentials**: Support for authentication headers
3. **TLS**: Support for secure endpoints
4. **Data Sanitization**: Mask sensitive values in attributes

## Documentation Structure

### README.md
- Quick start
- Installation
- Basic usage
- Configuration options
- Examples

### ARCHITECTURE.md
- This document

### docs/configuration.md
- All configuration options
- Environment variables
- Configuration file format

### docs/attributes.md
- Semantic conventions
- Attribute reference
- Baggage specification

### docs/backends.md
- Jaeger setup
- Grafana Tempo setup
- AWS X-Ray setup
- Custom backends

## Success Metrics

1. **Adoption**: GitHub stars, PyPI downloads
2. **Performance**: <5% overhead on test execution
3. **Compatibility**: Works with RF 6.0+, Python 3.8+
4. **Reliability**: >95% test coverage
5. **Usability**: Clear documentation, easy setup

## Future Enhancements

1. **Trace Context Propagation**: Inject trace context into HTTP requests
2. **Custom Instrumentation**: API for custom spans in test libraries
3. **Metrics Integration**: Export RF metrics alongside traces
4. **Dashboard Templates**: Pre-built Grafana dashboards
5. **CI/CD Integration**: GitHub Actions, GitLab CI examples
6. **Trace Analysis**: CLI tool to analyze traces
7. **Performance Regression**: Detect slow tests via trace analysis

## Contributing Guidelines

1. Fork repository
2. Create feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Run linters (black, ruff, mypy)
6. Submit pull request
7. Maintain >90% code coverage

## Release Strategy

- **Semantic Versioning**: MAJOR.MINOR.PATCH
- **Release Cadence**: Monthly for minor releases
- **Changelog**: Keep detailed CHANGELOG.md
- **PyPI**: Automated releases via GitHub Actions
- **Compatibility**: Support RF versions for 2 years

## References

- [Robot Framework Listener API](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#listener-interface)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)
- [Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)

## Contact & Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Slack**: #robotframework-tracer on RF Slack
- **Email**: maintainer@example.com

---

**Status**: Planning Phase  
**Last Updated**: 2025-12-09  
**Version**: 0.1.0-alpha
