*** Settings ***
Documentation     Test suite with nested keywords

*** Test Cases ***
Test With Custom Keyword
    [Tags]    custom
    My Custom Keyword

Test With Nested Keywords
    [Tags]    nested
    Outer Keyword

*** Keywords ***
My Custom Keyword
    Log    Inside custom keyword
    Should Be True    ${True}

Outer Keyword
    Log    Outer keyword start
    Inner Keyword
    Log    Outer keyword end

Inner Keyword
    Log    Inner keyword executing
    Should Not Be Empty    Hello
