# Fix: Add trace_id to Metrics for Per-Run Correlation

## Problem

Metrics were missing `trace_id` attribute, making it impossible to:
- Group metrics by execution run
- Calculate per-run pass/fail rates
- Correlate metrics to traces for drill-down analysis

## Solution

Added `trace_id` attribute to all metrics by extracting it from the current span context.

## Changes Made

### 1. Test Metrics (`end_test`)
- `rf.tests.total` - now includes `trace_id`
- `rf.tests.passed` - now includes `trace_id`
- `rf.tests.failed` - now includes `trace_id`
- `rf.tests.skipped` - now includes `trace_id`
- `rf.test.duration` - now includes `trace_id`

### 2. Suite Metrics (`end_suite`)
- `rf.suite.duration` - now includes `trace_id`

### 3. Keyword Metrics (`end_keyword`)
- `rf.keywords.executed` - now includes `trace_id`
- `rf.keyword.duration` - now includes `trace_id`

## Metric Attributes (After Fix)

| Metric | Attributes |
|--------|-----------|
| `rf.tests.total` | `suite`, `trace_id` |
| `rf.tests.passed` | `suite`, `trace_id` |
| `rf.tests.failed` | `suite`, `trace_id`, `tags` |
| `rf.tests.skipped` | `suite`, `trace_id` |
| `rf.test.duration` | `suite`, `trace_id`, `status` |
| `rf.suite.duration` | `suite`, `trace_id`, `status` |
| `rf.keywords.executed` | `type`, `trace_id` |
| `rf.keyword.duration` | `type`, `trace_id`, `status` |

## Usage Examples

### Per-Run Pass Rate
```
SELECT 
  trace_id,
  SUM(rf.tests.passed) / SUM(rf.tests.total) as pass_rate
FROM metrics
GROUP BY trace_id
ORDER BY timestamp DESC
LIMIT 10
```

### Failed Services Per Run
```
SELECT 
  trace_id,
  suite,
  SUM(rf.tests.failed) as failures
FROM metrics
WHERE rf.tests.failed > 0
GROUP BY trace_id, suite
```

### Correlate Metrics to Traces
```
# Get trace_id from metrics
trace_id = "abc123..."

# Query traces with same trace_id for drill-down
GET /traces?trace_id=abc123...
```

## Testing

To test the changes:
```bash
cd /home/epkcfsm/src/epos/repos
./run-test.sh scas

# Check metrics in SigNoz - they should now have trace_id attribute
```

## Next Steps

1. Rebuild robotframework-tracer package
2. Update epos-repos-test Docker image
3. Deploy to Kubernetes
4. Create SigNoz dashboards using trace_id for per-run analysis
