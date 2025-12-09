# Attribute Reference

Complete reference for all span attributes in robotframework-tracer.

## Attribute Naming Convention

All Robot Framework attributes use the `rf.` prefix following OpenTelemetry semantic conventions.

## Suite Attributes

Attributes attached to suite spans (root spans).

### `rf.suite.name`
- **Type**: String
- **Description**: Name of the test suite
- **Example**: `Example Test`, `API Tests`

### `rf.suite.id`
- **Type**: String
- **Description**: Unique identifier for the suite
- **Example**: `s1`, `s1-s2`

### `rf.suite.source`
- **Type**: String
- **Description**: File path of the test suite
- **Example**: `/path/to/tests/example.robot`

### `rf.suite.metadata.{key}`
- **Type**: String
- **Description**: Suite metadata key-value pairs
- **Example**: 
  - `rf.suite.metadata.author`: `John Doe`
  - `rf.suite.metadata.version`: `1.0.0`
  - `rf.suite.metadata.environment`: `staging`

## Test Attributes

Attributes attached to test case spans.

### `rf.test.name`
- **Type**: String
- **Description**: Name of the test case
- **Example**: `Simple Passing Test`, `Login Test`

### `rf.test.id`
- **Type**: String
- **Description**: Unique identifier for the test
- **Example**: `s1-t1`, `s1-s2-t3`

### `rf.test.tags`
- **Type**: Array of Strings
- **Description**: Tags assigned to the test
- **Example**: `["smoke", "regression"]`, `["api", "critical"]`

### `rf.test.template`
- **Type**: String
- **Description**: Test template if used
- **Example**: `Login With Credentials`

### `rf.test.timeout`
- **Type**: String
- **Description**: Test timeout if configured
- **Example**: `5 minutes`, `30 seconds`

## Keyword Attributes

Attributes attached to keyword/test step spans.

### `rf.keyword.name`
- **Type**: String
- **Description**: Name of the keyword
- **Example**: `Log`, `Should Be Equal`, `My Custom Keyword`

### `rf.keyword.type`
- **Type**: String
- **Description**: Type of keyword
- **Values**: `KEYWORD`, `SETUP`, `TEARDOWN`
- **Example**: `KEYWORD`, `SETUP`

### `rf.keyword.library`
- **Type**: String
- **Description**: Library that provides the keyword
- **Example**: `BuiltIn`, `SeleniumLibrary`, `RequestsLibrary`

### `rf.keyword.args`
- **Type**: String
- **Description**: Comma-separated keyword arguments
- **Example**: `Hello, World`, `id=username, admin`
- **Note**: Limited by `RF_TRACER_MAX_ARG_LENGTH` (default: 200)

## Result Attributes

Attributes related to execution results.

### `rf.status`
- **Type**: String
- **Description**: Execution status
- **Values**: `PASS`, `FAIL`, `SKIP`, `NOT_RUN`
- **Example**: `PASS`, `FAIL`

### `rf.elapsed_time`
- **Type**: Float
- **Description**: Execution duration in seconds
- **Example**: `0.128`, `2.456`

### `rf.start_time`
- **Type**: String
- **Description**: Start timestamp
- **Format**: `YYYYMMDD HH:MM:SS.mmm`
- **Example**: `20251209 14:50:46.478`

### `rf.end_time`
- **Type**: String
- **Description**: End timestamp
- **Format**: `YYYYMMDD HH:MM:SS.mmm`
- **Example**: `20251209 14:50:46.606`

### `rf.message`
- **Type**: String
- **Description**: Result message (usually for failures)
- **Example**: `Expected != Actual`, `Element not found`

## Framework Attributes

Attributes related to the Robot Framework itself.

### `rf.version`
- **Type**: String
- **Description**: Robot Framework version
- **Example**: `7.0.0`, `6.1.1`

## Baggage

Baggage is propagated from suite spans to all child spans.

### `rf.suite.id`
- **Description**: Suite identifier
- **Propagation**: All child spans

### `rf.version`
- **Description**: Robot Framework version
- **Propagation**: All child spans

### `rf.suite.metadata.{key}`
- **Description**: Suite metadata (limited to 5 items)
- **Propagation**: All child spans

## Span Events

Events attached to spans for specific occurrences.

### `test.failed`
- **Attached to**: Test and keyword spans
- **Attributes**:
  - `message`: Failure message
  - `rf.status`: `FAIL`
  - `exception.type`: Exception type (if available)
  - `exception.message`: Exception message (if available)
  - `timestamp`: Failure timestamp

### `setup.start`
- **Attached to**: Setup keyword spans
- **Attributes**:
  - `keyword`: Keyword name

### `setup.end`
- **Attached to**: Setup keyword spans
- **Attributes**:
  - `keyword`: Keyword name
  - `status`: Execution status

### `teardown.start`
- **Attached to**: Teardown keyword spans
- **Attributes**:
  - `keyword`: Keyword name

### `teardown.end`
- **Attached to**: Teardown keyword spans
- **Attributes**:
  - `keyword`: Keyword name
  - `status`: Execution status

## Example Span with Attributes

### Suite Span
```json
{
  "name": "📦 Example Test",
  "attributes": {
    "rf.suite.name": "Example Test",
    "rf.suite.id": "s1",
    "rf.suite.source": "/path/to/example.robot",
    "rf.suite.metadata.author": "John Doe",
    "rf.suite.metadata.version": "1.0.0",
    "rf.start_time": "20251209 14:50:46.478",
    "rf.end_time": "20251209 14:50:46.606",
    "rf.elapsed_time": "0.128",
    "rf.status": "PASS",
    "rf.version": "7.0.0"
  },
  "baggage": {
    "rf.suite.id": "s1",
    "rf.version": "7.0.0",
    "rf.suite.metadata.author": "John Doe"
  }
}
```

### Test Span
```json
{
  "name": "🧪 Simple Passing Test",
  "attributes": {
    "rf.test.name": "Simple Passing Test",
    "rf.test.id": "s1-t1",
    "rf.test.tags": ["smoke", "example"],
    "rf.start_time": "20251209 14:50:46.480",
    "rf.end_time": "20251209 14:50:46.520",
    "rf.elapsed_time": "0.040",
    "rf.status": "PASS"
  }
}
```

### Keyword Span
```json
{
  "name": "👟 Should Be Equal Hello, Hello",
  "attributes": {
    "rf.keyword.name": "Should Be Equal",
    "rf.keyword.type": "KEYWORD",
    "rf.keyword.library": "BuiltIn",
    "rf.keyword.args": "Hello, Hello",
    "rf.status": "PASS",
    "rf.elapsed_time": "0.001"
  }
}
```

### Failed Test with Error Event
```json
{
  "name": "🧪 Failing Test Example",
  "attributes": {
    "rf.test.name": "Failing Test Example",
    "rf.test.id": "s1-t4",
    "rf.status": "FAIL",
    "rf.message": "Expected != Actual",
    "rf.elapsed_time": "0.015"
  },
  "events": [
    {
      "name": "test.failed",
      "attributes": {
        "message": "Expected != Actual",
        "rf.status": "FAIL",
        "timestamp": "20251209 14:50:46.606"
      }
    }
  ]
}
```

## Querying Attributes in Jaeger

### Find all failed tests
```
rf.status=FAIL
```

### Find tests with specific tag
```
rf.test.tags=smoke
```

### Find tests from specific suite
```
rf.suite.name="Example Test"
```

### Find slow tests (>5 seconds)
```
rf.elapsed_time>5.0
```

## Best Practices

### 1. Use Tags for Filtering
Add meaningful tags to tests for easy filtering:
```robot
*** Test Cases ***
Login Test
    [Tags]    smoke    api    critical
```

### 2. Add Suite Metadata
Provide context via suite metadata:
```robot
*** Settings ***
Metadata    Author    John Doe
Metadata    Version    1.0.0
Metadata    Environment    staging
```

### 3. Monitor Timing Attributes
Use `rf.elapsed_time`, `rf.start_time`, `rf.end_time` to:
- Identify slow tests
- Track performance trends
- Detect regressions

### 4. Leverage Baggage
Baggage propagates to all child spans, useful for:
- Distributed tracing across services
- Correlation with application traces
- Filtering related spans

## See Also

- [Configuration Reference](configuration.md)
- [Span Naming Convention](span-naming.md)
- [Backend Setup](backends.md)
