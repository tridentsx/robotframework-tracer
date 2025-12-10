*** Settings ***
Documentation    Simple test for trace context propagation

*** Test Cases ***
Simple Trace Context Test
    [Documentation]    Basic test to check if trace variables are available
    Log    Starting test
    
    # Try to access variables with error handling
    ${trace_id_available}=    Run Keyword And Return Status    Variable Should Exist    ${TRACE_ID}
    ${headers_available}=     Run Keyword And Return Status    Variable Should Exist    ${TRACE_HEADERS}
    
    Log    Trace ID available: ${trace_id_available}
    Log    Headers available: ${headers_available}
    
    IF    ${trace_id_available}
        Log    Trace ID: ${TRACE_ID}
    ELSE
        Log    Trace ID not available
    END
    
    IF    ${headers_available}
        Log    Trace Headers: ${TRACE_HEADERS}
    ELSE
        Log    Trace Headers not available
    END
