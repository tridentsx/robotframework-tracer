*** Settings ***
Documentation    Test trace context propagation to Robot Framework variables
Library          Collections
Library          DateTime

*** Test Cases ***
Test Trace Context Variables Available
    [Documentation]    Verify that trace context is available as RF variables
    Log    Trace Headers: ${TRACE_HEADERS}
    Log    Trace ID: ${TRACE_ID}
    Log    Span ID: ${SPAN_ID}
    Log    Traceparent: ${TRACEPARENT}
    
    # Verify variables are set and not empty
    Should Not Be Empty    ${TRACE_HEADERS}
    Should Not Be Empty    ${TRACE_ID}
    Should Not Be Empty    ${SPAN_ID}
    Should Not Be Empty    ${TRACEPARENT}
    
    # Verify trace ID format (32 hex chars)
    Should Match Regexp    ${TRACE_ID}    ^[0-9a-f]{32}$
    
    # Verify span ID format (16 hex chars)
    Should Match Regexp    ${SPAN_ID}    ^[0-9a-f]{16}$
    
    # Verify traceparent format (W3C standard)
    Should Match Regexp    ${TRACEPARENT}    ^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$

Test HTTP Headers Format
    [Documentation]    Verify HTTP headers are properly formatted
    Log    HTTP Headers: ${TRACE_HEADERS}
    
    # Should be a dictionary with traceparent
    Should Be True    isinstance($TRACE_HEADERS, dict)
    Dictionary Should Contain Key    ${TRACE_HEADERS}    traceparent
    
    # Traceparent should match W3C format
    ${traceparent}=    Get From Dictionary    ${TRACE_HEADERS}    traceparent
    Should Match Regexp    ${traceparent}    ^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$

Test Diameter Protocol Usage
    [Documentation]    Example of using trace context in Diameter protocol
    Log    Building Diameter message with trace context
    
    # Example: Add trace ID as Diameter AVP
    ${diameter_msg}=    Create Dictionary
    ...    command_code=272    # Credit-Control-Request
    ...    trace_id=${TRACE_ID}
    ...    span_id=${SPAN_ID}
    
    Log    Diameter message: ${diameter_msg}
    Should Contain    ${diameter_msg}[trace_id]    ${TRACE_ID}

Test Custom Protocol Usage
    [Documentation]    Example of using individual trace components
    Log    Custom protocol with trace context
    
    # Get current timestamp
    ${current_time}=    Get Current Date    result_format=%Y%m%d%H%M%S
    
    # Build custom message with trace components
    ${custom_msg}=    Catenate    SEPARATOR=|
    ...    MSG_TYPE=REQUEST
    ...    TRACE_ID=${TRACE_ID}
    ...    SPAN_ID=${SPAN_ID}
    ...    TIMESTAMP=${current_time}
    
    Log    Custom message: ${custom_msg}
    Should Contain    ${custom_msg}    TRACE_ID=${TRACE_ID}
    Should Contain    ${custom_msg}    SPAN_ID=${SPAN_ID}
