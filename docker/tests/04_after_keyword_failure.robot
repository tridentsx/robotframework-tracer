*** Settings ***
Documentation     Scenario: screenshot captured after keyword failure
...               Uses SeleniumLibrary with headless Chrome
...               Tests the common CI pattern of screenshot-on-failure
Library           SeleniumLibrary
Library           OperatingSystem
Resource          selenium_setup.resource
Suite Setup       Open Headless Chrome    ${OUT}
Suite Teardown    Close All Browsers

*** Variables ***
${OUT}    /output/screenshots/failure

*** Test Cases ***
Screenshot In Teardown After Failure
    [Documentation]    Take screenshot in test teardown after assertion fails
    [Teardown]    Capture Screenshot On Failure    failure_teardown.png
    Go To    https://www.google.com
    Run Keyword And Expect Error    *
    ...    Element Should Be Visible    id=nonexistent_xyz    timeout=1s

Screenshot After Continue On Failure
    [Documentation]    Screenshot taken inside error handler after failure
    Go To    https://www.google.com
    ${status}=    Run Keyword And Return Status
    ...    Element Should Be Visible    id=also_nonexistent    timeout=1s
    Should Be Equal    ${status}    ${FALSE}
    Capture Page Screenshot    ${OUT}/failure_continue.png

Screenshot After Successful Recovery
    [Documentation]    Screenshot after error handling — verifies normal flow resumes
    Go To    https://www.google.com
    ${status}=    Run Keyword And Return Status
    ...    Element Should Be Visible    id=nope    timeout=1s
    Run Keyword If    not ${status}
    ...    Capture Page Screenshot    ${OUT}/failure_recovery.png

*** Keywords ***
Capture Screenshot On Failure
    [Arguments]    ${filename}
    Capture Page Screenshot    ${OUT}/${filename}
