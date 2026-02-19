# Trace Context Propagation

The `robotframework-tracer` supports both inbound and outbound trace context propagation.

## Inbound: Inheriting Parent Trace Context

When the `TRACEPARENT` environment variable is set, the listener automatically makes the suite span a child of the external parent trace. This follows the [W3C Trace Context](https://www.w3.org/TR/trace-context/) standard.

### Use Cases

- **CI/CD pipelines**: Correlate test execution with pipeline traces
- **Parallel execution (pabot)**: A wrapper script creates a parent span and sets `TRACEPARENT` for worker processes, producing a unified trace across all parallel workers
- **Nested orchestration**: Any parent process that sets `TRACEPARENT` before invoking Robot Framework

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TRACEPARENT` | Yes | W3C traceparent header (e.g. `00-{trace_id}-{span_id}-01`) |
| `TRACESTATE` | No | W3C tracestate header for vendor-specific data |

### Example: Pabot with Unified Traces

```python
# trace_wrapper.py - creates parent span for pabot workers
from opentelemetry import trace
from opentelemetry.propagate import inject
import subprocess, os

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("Pabot Parallel Execution") as span:
    headers = {}
    inject(headers)

    env = os.environ.copy()
    env["TRACEPARENT"] = headers["traceparent"]

    subprocess.run(["pabot", "--processes", "4", "--listener",
        "robotframework_tracer.TracingListener", "tests/"], env=env)
```

This produces a trace like:
```
Pabot Parallel Execution          (closed immediately — visible in trace viewer right away)
├── Execution Started             (signal span, closed immediately)
├── Test Starting: TC01           (signal span, visible within seconds)
├── Test Starting: TC02           (signal span, visible within seconds)
├── Test Starting: TC03           (signal span, visible within seconds)
├── Long Running Suite - TC01     (suite span, appears when worker finishes)
│   └── TC01 - Fibonacci...
├── Long Running Suite - TC02     (suite span, appears when worker finishes)
│   └── TC02 - Nested Keywords...
└── Execution Finished            (signal span, closed at end)
```

> **Note:** While tests are still running, suite spans that haven't been exported yet may appear as "Missing Span" in SigNoz/Jaeger. This is normal — they are replaced with the real span names once the worker finishes and exports them.

### Live Visibility

When using `trace_wrapper.py` with pabot, the tracer provides live visibility into running tests:

1. The wrapper creates a root span and closes it immediately so the trace appears in your backend right away
2. Each worker emits a "Test Starting: {name}" signal span under the root when a test begins
3. Suite spans are renamed to include the test name (e.g. "Long Running Suite - My Test")
4. Signal spans are exported via the normal `BatchSpanProcessor` cycle (~5 seconds), no `force_flush()` overhead

This means you can see which tests are running in your trace viewer within seconds, instead of waiting for the entire suite to finish.

### Example: CI Pipeline

```bash
# In your CI script, export TRACEPARENT from the pipeline's trace context
export TRACEPARENT="00-$(openssl rand -hex 16)-$(openssl rand -hex 8)-01"
robot --listener robotframework_tracer.TracingListener tests/
```

## Outbound: Propagating Context to Your SUT

When a test starts, the following variables are automatically set:

### HTTP Headers
- **`${TRACE_HEADERS}`** - Dictionary with HTTP headers for trace propagation
  ```robot
  POST    http://my-api/endpoint    headers=${TRACE_HEADERS}
  ```

### Individual Components
- **`${TRACE_ID}`** - 32-character hex trace ID
- **`${SPAN_ID}`** - 16-character hex span ID  
- **`${TRACEPARENT}`** - W3C traceparent header value
- **`${TRACESTATE}`** - W3C tracestate header value (if present)

## Usage Examples

### HTTP/REST APIs
```robot
*** Test Cases ***
Test API With Tracing
    ${response}=    POST    http://my-sut/api
    ...    json={"data": "test"}
    ...    headers=${TRACE_HEADERS}
    
    Should Be Equal As Integers    ${response.status_code}    200
```

### Diameter Protocol
```robot
*** Test Cases ***
Test Diameter With Tracing
    ${diameter_request}=    Create Diameter CCR
    ...    command_code=272
    ...    session_id=session123
    ...    trace_id=${TRACE_ID}
    ...    span_id=${SPAN_ID}
    
    ${response}=    Send Diameter Request    ${diameter_request}
    Should Be Equal    ${response.result_code}    2001
```

### Custom Protocols
```robot
*** Test Cases ***
Test Custom Protocol With Tracing
    # Build custom message with trace context
    ${message}=    Catenate    SEPARATOR=|
    ...    MSG_TYPE=REQUEST
    ...    TRACE_ID=${TRACE_ID}
    ...    SPAN_ID=${SPAN_ID}
    ...    PAYLOAD=test_data
    
    ${response}=    Send Custom Message    ${message}
    Should Contain    ${response}    SUCCESS
```

### Manual Header Construction
```robot
*** Test Cases ***
Test Manual Headers
    # For protocols that need custom header formats
    ${custom_headers}=    Create Dictionary
    ...    X-Trace-Id=${TRACE_ID}
    ...    X-Span-Id=${SPAN_ID}
    ...    X-Traceparent=${TRACEPARENT}
    
    ${response}=    GET    http://my-api/data    headers=${custom_headers}
```

## Variable Formats

### TRACE_HEADERS
Dictionary containing standard OpenTelemetry propagation headers:
```python
{
    'traceparent': '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01',
    'tracestate': 'vendor1=value1,vendor2=value2'  # Optional
}
```

### TRACE_ID
32-character lowercase hexadecimal string:
```
4bf92f3577b34da6a3ce929d0e0e4736
```

### SPAN_ID  
16-character lowercase hexadecimal string:
```
00f067aa0ba902b7
```

### TRACEPARENT
W3C Trace Context format:
```
00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```
Format: `{version}-{trace-id}-{parent-id}-{trace-flags}`

## SUT Integration

Your System Under Test needs to:

1. **Extract trace context** from the protocol
2. **Create child spans** using the received context
3. **Continue propagation** to downstream services

### Example: Python SUT
```python
from opentelemetry import trace
from opentelemetry.propagate import extract

# HTTP endpoint
@app.route('/api', methods=['POST'])
def handle_request():
    # Extract context from HTTP headers
    context = extract(request.headers)
    
    # Create child span
    with tracer.start_as_current_span("sut_operation", context=context):
        # Your business logic
        result = process_request(request.json)
        return {"result": result}

# Custom protocol handler
def handle_diameter_request(message):
    # Extract trace context from Diameter AVPs
    trace_id = message.get('trace_id')
    span_id = message.get('span_id')
    
    if trace_id and span_id:
        # Reconstruct span context
        span_context = trace.SpanContext(
            trace_id=int(trace_id, 16),
            span_id=int(span_id, 16),
            is_remote=True
        )
        context = trace.set_span_in_context(trace.NonRecordingSpan(span_context))
        
        # Create child span
        with tracer.start_as_current_span("diameter_operation", context=context):
            return process_diameter_request(message)
```

## Distributed Trace Flow

```
Robot Framework Test
├── HTTP Request (with traceparent header)
│   └── SUT Service A
│       ├── Database Query
│       └── HTTP Call to Service B
│           └── Service B Operation
└── Diameter Request (with trace_id AVP)
    └── SUT Service C
        └── External API Call
```

All spans appear in the same distributed trace, enabling end-to-end observability.

## Requirements

- Robot Framework 6.0+
- OpenTelemetry SDK
- SUT must support trace context extraction

## Troubleshooting

### Variables Not Available
- Ensure you're using the listener: `--listener robotframework_tracer.TracingListener`
- Variables are only set during test execution (not in suite setup/teardown)

### Empty Variables
- Check that spans are being created (listener is working)
- Verify Robot Framework BuiltIn library is available

### SUT Not Receiving Context
- Verify headers/fields are being sent correctly
- Check SUT trace context extraction logic
- Ensure OpenTelemetry propagators are configured

## Best Practices

1. **Always check variable availability** before using
2. **Log trace context** for debugging
3. **Handle missing context gracefully** in SUT
4. **Use appropriate format** for your protocol
5. **Validate trace ID formats** if needed

```robot
*** Test Cases ***
Robust Trace Propagation
    # Check if tracing is available
    ${has_trace}=    Run Keyword And Return Status
    ...    Should Not Be Empty    ${TRACE_ID}
    
    IF    ${has_trace}
        Log    Using trace context: ${TRACE_ID}
        ${headers}=    Set Variable    ${TRACE_HEADERS}
    ELSE
        Log    No trace context available
        ${headers}=    Create Dictionary
    END
    
    ${response}=    POST    http://my-api/endpoint    headers=${headers}
```
