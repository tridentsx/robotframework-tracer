# Logs Implementation - RESOLVED

## Status: ✅ IMPLEMENTED

Robot Framework logs are now properly sent to observability backends via the **OpenTelemetry Logs API**.

## Implementation

Logs are sent to `/v1/logs` endpoint using the OTel Logs API with:
- Full trace correlation (trace_id, span_id)
- Proper severity mapping
- Service name from resource attributes
- Automatic context propagation from active spans

## Usage

```bash
robot --listener "robotframework_tracer.TracingListener:capture_logs=true:log_level=INFO" tests/
```

## What's Sent

**Traces** → `/v1/traces`:
- Suite, test, and keyword spans
- Execution hierarchy and timing

**Logs** → `/v1/logs`:
- Log messages from Robot Framework
- Correlated to traces via trace_id/span_id
- Visible in observability backend's Logs UI

## Verification

Logs appear in SigNoz/Grafana/etc. Logs UI with:
- Service name
- Trace correlation
- Ability to jump between logs ↔ traces

See `TESTING_CENTRALIZED_OTEL.md` for test examples.
