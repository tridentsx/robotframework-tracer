*** Settings ***
Documentation     Web testing example with suite setup/teardown
Suite Setup       Initialize Test Environment
Suite Teardown    Cleanup Test Environment
Library           RequestsLibrary
Library           Collections

*** Variables ***
${BASE_URL}       https://www.google.com
${TIMEOUT}        10

*** Test Cases ***
Test Google Homepage Access
    [Tags]    web    smoke
    [Documentation]    Verify Google homepage is accessible
    ${response}=    GET    ${BASE_URL}
    Should Be Equal As Integers    ${response.status_code}    200
    Should Contain    ${response.text}    Google
    Log    Successfully accessed Google homepage

Test Google Search API
    [Tags]    web    api
    [Documentation]    Test Google search functionality
    ${params}=    Create Dictionary    q=robot framework
    ${response}=    GET    ${BASE_URL}/search    params=${params}
    Should Be Equal As Integers    ${response.status_code}    200
    Log    Search request completed with status: ${response.status_code}

Test Multiple HTTP Status Codes
    [Tags]    web    status
    [Documentation]    Test various HTTP endpoints
    Test HTTP Status    ${BASE_URL}    200
    Test HTTP Status    https://httpbin.org/status/404    404
    Test HTTP Status    https://httpbin.org/status/500    500

Test Request Headers
    [Tags]    web    headers
    [Documentation]    Verify request headers are sent correctly
    ${headers}=    Create Dictionary    User-Agent=RobotFramework-Test
    ${response}=    GET    https://httpbin.org/headers    headers=${headers}
    Should Be Equal As Integers    ${response.status_code}    200
    Should Contain    ${response.text}    RobotFramework-Test
    Log    Headers verified successfully

Test Connection Timeout Handling
    [Tags]    web    timeout    negative
    [Documentation]    Test timeout handling for slow endpoints
    Run Keyword And Expect Error    *    
    ...    GET    https://httpbin.org/delay/15    timeout=2

Test JSON Response Parsing
    [Tags]    web    json
    [Documentation]    Test JSON response handling
    ${response}=    GET    https://httpbin.org/json
    Should Be Equal As Integers    ${response.status_code}    200
    ${json_data}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json_data}    slideshow
    Log    JSON response parsed successfully

*** Keywords ***
Initialize Test Environment
    [Documentation]    Setup test environment and verify connectivity
    Log    Starting test suite: ${SUITE NAME}
    Log    Test environment: ${CURDIR}
    Create Session    google    ${BASE_URL}    timeout=${TIMEOUT}
    Log    Test environment initialized successfully

Cleanup Test Environment
    [Documentation]    Clean up test environment
    Log    Cleaning up test environment
    Delete All Sessions
    Log    Test suite completed: ${SUITE NAME}

Test HTTP Status
    [Arguments]    ${url}    ${expected_status}
    [Documentation]    Helper keyword to test HTTP status codes
    Log    Testing URL: ${url} (expecting ${expected_status})
    ${response}=    GET    ${url}    expected_status=any
    Should Be Equal As Integers    ${response.status_code}    ${expected_status}
    Log    Status code ${expected_status} verified for ${url}
