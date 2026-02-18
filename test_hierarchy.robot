*** Settings ***
Suite Setup       Suite Setup Keyword
Suite Teardown    Suite Teardown Keyword

*** Test Cases ***
Test One
    Log    Test one executing

Test Two
    Log    Test two executing

*** Keywords ***
Suite Setup Keyword
    Log    Suite is starting

Suite Teardown Keyword
    Log    Suite is ending
