# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial implementation of Robot Framework OpenTelemetry tracer
- Support for suite, test, and keyword span creation
- Comprehensive attribute extraction (metadata, timing, tags)
- Span prefix styles (none, text, emoji)
- Log message capture with level filtering
- Sampling support (TraceIdRatioBased)
- gRPC exporter support (optional)
- Automatic resource detection (host, OS, Python, RF versions)
- Baggage propagation for distributed tracing
- Enhanced error reporting with detailed events
- Setup/teardown event tracking
- Configurable via environment variables
- Full integration with Jaeger, Tempo, Zipkin

### Changed
- Service name default changed from `robot-framework` to `rf`
- Span names now include keyword arguments
- Error events include exception type and timestamp

### Fixed
- Log message capture recursion issue
- Timestamp attribute type conversion
- Mock import issues in tests

## [0.1.0] - 2025-12-09

### Added
- Initial MVP release
- Basic tracing functionality
- HTTP OTLP exporter
- Configuration via environment variables
- Unit and integration tests
- Example with Jaeger
- Comprehensive documentation

[Unreleased]: https://github.com/yourusername/robotframework-tracer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/robotframework-tracer/releases/tag/v0.1.0
