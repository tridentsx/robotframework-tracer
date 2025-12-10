# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
