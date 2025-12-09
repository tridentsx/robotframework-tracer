*** Settings ***
Documentation     Simple test suite for integration testing

*** Test Cases ***
Passing Test
    [Tags]    smoke
    Log    This test will pass
    Should Be Equal    1    1

Failing Test
    [Tags]    negative
    Log    This test will fail
    Should Be Equal    1    2    Values should be equal

Test With Multiple Keywords
    [Tags]    keywords
    Log    First keyword
    Log    Second keyword
    Should Be True    ${True}
