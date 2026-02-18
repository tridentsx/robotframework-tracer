# Robot Framework Tracer v0.4.0 - Metrics Release

## Overview

Version 0.4.0 adds **OpenTelemetry Metrics** to complete the observability stack with traces, logs, and metrics.

## What's New

### OpenTelemetry Metrics 📊

Automatic emission of test execution metrics for monitoring, alerting, and trend analysis:

**Test Metrics:**
- `rf.tests.total` - Total tests executed (with suite dimension)
- `rf.tests.passed` - Tests that passed
- `rf.tests.failed` - Tests that failed (with suite and tag dimensions)
- `rf.tests.skipped` - Tests that were skipped

**Duration Metrics (Histograms):**
- `rf.test.duration` - Test execution time (with suite and status dimensions)
- `rf.suite.duration` - Suite execution time (with suite and status dimensions)
- `rf.keyword.duration` - Keyword execution time (with keyword, type, and status dimensions)

**Keyword Metrics:**
- `rf.keywords.executed` - Total keywords executed (with type dimension)

**Metric Dimensions:**
- `suite` - Suite name
- `status` - PASS/FAIL/SKIP
- `tag` - Test tags (for failure analysis)
- `type` - Keyword type (SETUP/TEARDOWN/KEYWORD)
- `keyword` - Keyword name

### Use Cases

**Dashboards:**
- Visualize test pass rate over time
- Track test execution duration trends
- Monitor keyword performance

**Alerting:**
- Alert when pass rate drops below threshold
- Alert on execution time increases
- Notify on failure spikes

**Analysis:**
- Group failures by suite or tag
- Identify slow tests or keywords
- Track test suite growth

### Configuration

**No configuration needed!** Metrics are automatically enabled and sent to `/v1/metrics` endpoint.

Metrics share the same:
- Service name as traces/logs
- Resource attributes
- OTLP endpoint (automatically derived)

### Complete Observability Stack

| Signal | Endpoint | Purpose |
|--------|----------|---------|
| **Traces** | `/v1/traces` | Execution flow and timing |
| **Logs** | `/v1/logs` | Detailed messages with trace correlation |
| **Metrics** | `/v1/metrics` | Aggregated statistics and trends |

## Example Metrics

After running 4 tests (3 passed, 1 failed):

```
rf.tests.total{suite="Example Test"} = 4
rf.tests.passed{suite="Example Test"} = 3
rf.tests.failed{suite="Example Test"} = 1
rf.tests.failed{tag="negative"} = 1
rf.test.duration{suite="Example Test", status="PASS"} = [histogram]
rf.suite.duration{suite="Example Test", status="FAIL"} = 1234ms
rf.keywords.executed{type="KEYWORD"} = 15
rf.keyword.duration{keyword="Log", type="KEYWORD", status="PASS"} = [histogram]
```

## Migration from v0.3.0

**No breaking changes!** Metrics are automatically enabled.

**Action Required:**
- Ensure your observability backend accepts metrics at `/v1/metrics`
- Check Metrics UI for new `rf.*` metrics

## Testing

Tested with:
- ✅ SigNoz (centralized OTel stack)
- ✅ Metrics properly emitted
- ✅ Dimensions correctly set
- ✅ Histograms working
- ✅ No performance impact

## Quick Start

```bash
# Run tests - metrics automatically emitted
robot --listener "robotframework_tracer.TracingListener:capture_logs=true" tests/
```

**Check your observability backend:**
- **Traces UI**: Execution flow
- **Logs UI**: Correlated log messages  
- **Metrics UI**: Test execution statistics ✨ NEW

## Compatibility

- **Robot Framework**: 6.0+
- **Python**: 3.8+
- **OpenTelemetry**: Latest SDK
- **Backends**: Any OTLP-compatible backend (Jaeger, SigNoz, Grafana, etc.)

## What's Next

Future enhancements:
- Custom metric dimensions
- Configurable export interval
- Additional performance metrics
- Enhanced failure analysis

---

**Version**: 0.4.0  
**Release Date**: 2026-02-18  
**Status**: Production Ready ✅

