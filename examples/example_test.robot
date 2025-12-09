*** Settings ***
Documentation     Example test suite to demonstrate tracing

*** Test Cases ***
Simple Passing Test
    [Tags]    smoke    example
    Log    Starting simple test
    Should Be Equal    Hello    Hello
    Log    Test completed successfully

Test With Multiple Steps
    [Tags]    example
    Log    Step 1: Initialize
    Sleep    0.1s
    Log    Step 2: Execute
    Should Be True    ${True}
    Log    Step 3: Verify
    Should Not Be Empty    Test Data

Test With Custom Keyword
    [Tags]    example    custom
    My Custom Keyword    Hello World

Failing Test Example
    [Tags]    example    negative
    Log    This test demonstrates failure tracing
    Should Be Equal    Expected    Actual    This will fail

*** Keywords ***
My Custom Keyword
    [Arguments]    ${message}
    Log    Custom keyword called with: ${message}
    Should Not Be Empty    ${message}
    Log    Custom keyword completed
