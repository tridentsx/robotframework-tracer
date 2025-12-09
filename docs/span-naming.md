# Span Naming Convention

## Overview

Span names in robotframework-tracer follow the Robot Framework test step format, making traces easy to read and understand.

## Naming Format

### Suite Spans
**Format**: `{suite_name}`

**Example**: `Example Test`

### Test Spans
**Format**: `{test_name}`

**Example**: `Simple Passing Test`

### Keyword Spans
**Format**: `{keyword_name} {arg1}, {arg2}, ...`

**Examples**:
- `Log Starting simple test`
- `Should Be Equal Hello, Hello`
- `Sleep 0.1s`
- `My Custom Keyword Hello World`
- `Should Be Equal Expected, Actual, This will fail`

## Argument Handling

- All keyword arguments are included in the span name
- Arguments are joined with `, ` (comma-space)
- If the total argument string exceeds 100 characters, it's truncated with `...`
- Variables are shown as-is (e.g., `${message}`)

## Benefits

1. **Immediate Context**: See exactly what the keyword does without opening the span
2. **Easy Debugging**: Quickly identify which specific call failed
3. **Familiar Format**: Matches Robot Framework test step syntax
4. **Searchable**: Find specific keyword calls in Jaeger UI

## Examples from Jaeger UI

```
Example Test (suite)
├── Simple Passing Test (test)
│   ├── Log Starting simple test
│   ├── Should Be Equal Hello, Hello
│   └── Log Test completed successfully
├── Test With Multiple Steps (test)
│   ├── Log Step 1: Initialize
│   ├── Sleep 0.1s
│   ├── Log Step 2: Execute
│   ├── Should Be True ${True}
│   ├── Log Step 3: Verify
│   └── Should Not Be Empty Test Data
└── Failing Test Example (test)
    ├── Log This test demonstrates failure tracing
    └── Should Be Equal Expected, Actual, This will fail
```

## Configuration

The argument length limit can be adjusted via the `max_arg_length` configuration option (default: 200 characters for attributes, 100 for span names).

## Technical Details

- Span names are generated in `span_builder.py`
- Full arguments are still stored in span attributes (`rf.keyword.args`)
- Span name truncation is independent of attribute truncation
