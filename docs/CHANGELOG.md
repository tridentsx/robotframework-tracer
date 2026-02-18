# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-02-18

### Added
- **OpenTelemetry Metrics** - Automatic emission of test execution metrics
  - Test metrics: `rf.tests.total`, `rf.tests.passed`, `rf.tests.failed`, `rf.tests.skipped`
  - Duration histograms: `rf.test.duration`, `rf.suite.duration`, `rf.keyword.duration`
  - Keyword metrics: `rf.keywords.executed`
  - Dimensions: suite, status, tag, type, keyword
  - Metrics sent to `/v1/metrics` endpoint
- Metrics enable dashboards, alerting, and trend analysis

### Changed
- Metrics provider initialized automatically (no configuration needed)
- Metrics share same service name and resource attributes as traces/logs

## [0.3.0] - 2026-02-18

### Added
- **OpenTelemetry Logs API integration** - Logs sent to `/v1/logs` endpoint with trace correlation
- **OpenTelemetry Metrics** - Automatic emission of test execution metrics
  - Test metrics: `rf.tests.total`, `rf.tests.passed`, `rf.tests.failed`, `rf.tests.skipped`
  - Duration histograms: `rf.test.duration`, `rf.suite.duration`, `rf.keyword.duration`
  - Keyword metrics: `rf.keywords.executed`
  - Dimensions: suite, status, tag, type, keyword
- **Proper span hierarchy** - Fixed parent-child relationships using `trace.use_span()`
- Suite setup/teardown spans properly included in trace hierarchy

### Changed
- **Logs implementation** - Changed from span events to OpenTelemetry Logs API
  - Logs now appear in observability backend's Logs UI
  - Full trace correlation via trace_id and span_id
  - Logs sent to `/v1/logs` instead of embedded in traces
- **Span creation** - Use active span context for proper parent-child linking
- All spans now correctly appear as one unified trace instead of separate traces

### Fixed
- Span parent-child relationships now work correctly
- Logs properly correlated to traces with trace_id and span_id
- Service name properly set in logs and metrics

## [Unreleased]

### Added
- **Parent trace context support** from `TRACEPARENT`/`TRACESTATE` environment variables
- Suite spans inherit trace context from external parent processes (CI pipelines, wrapper scripts, pabot)
- W3C Trace Context compliant — reads standard `TRACEPARENT` and optional `TRACESTATE` env vars
- Documentation for parent trace context (`docs/trace-propagation.md`, `docs/configuration.md`)
- 5 new unit tests for parent context extraction and propagation
- **Local trace output file** — write spans as OTLP-compatible JSON to a local file alongside OTLP export
- `RF_TRACER_OUTPUT_FILE` env var / `trace_output_file` listener arg
- `RF_TRACER_OUTPUT_FORMAT` env var — `json` (default) or `gz` for gzip-compressed output
- `auto` mode generates filename from suite name + trace ID (e.g. `diverse_suite_4bf92f35_traces.json`)
- File is overwritten on each run
- 28 new unit tests for trace output file feature (92% total coverage)

### Changed
- `SpanBuilder.create_suite_span()` accepts optional `parent_context` parameter
- Updated ARCHITECTURE.md span hierarchy to reflect optional external parent

## [0.2.0] - 2025-12-10

### Added
- **Trace context propagation** to Robot Framework variables
- `${TRACE_HEADERS}` variable with HTTP headers for REST APIs
- `${TRACE_ID}` and `${SPAN_ID}` variables for custom protocols (Diameter, etc.)
- `${TRACEPARENT}` and `${TRACESTATE}` variables for W3C Trace Context
- Comprehensive documentation for trace propagation (`docs/trace-propagation.md`)
- Integration tests with HTTP, Diameter, and custom protocol examples
- 6 new unit tests for trace context functionality

### Changed
- Improved test coverage to 74% (from 72%)

## [0.2.0] - 2025-12-09

### Fixed
- Code formatting issues (black compliance)

## [0.1.1] - 2025-12-09

### Added
- GitHub repository topics for better discoverability
- Automated PyPI publishing via GitHub Actions
- Comprehensive PyPI publishing documentation

### Changed
- Moved all documentation files to docs/ folder
- Updated README links to reflect new documentation structure

## [0.1.0] - 2025-12-09

### Added
- Initial MVP release
- Basic tracing functionality
- HTTP OTLP exporter
- Configuration via environment variables
- Unit and integration tests
- Example with Jaeger
- Comprehensive documentation

[Unreleased]: https://github.com/tridentsx/robotframework-tracer/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/tridentsx/robotframework-tracer/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/tridentsx/robotframework-tracer/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/tridentsx/robotframework-tracer/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/tridentsx/robotframework-tracer/releases/tag/v0.1.0
