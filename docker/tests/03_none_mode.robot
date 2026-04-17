*** Settings ***
Documentation     Scenario: none mode — screenshots taken but NOT traced
...               Uses SeleniumLibrary with headless Chrome
Library           SeleniumLibrary
Library           OperatingSystem
Resource          selenium_setup.resource
Suite Setup       Open Headless Chrome    ${OUT}
Suite Teardown    Close All Browsers

*** Variables ***
${OUT}    /output/screenshots/none

*** Test Cases ***
None Mode Screenshot Exists On Disk But Not In Trace
    [Documentation]    Screenshot file is created but NO trace event should exist
    Go To    https://www.google.com
    ${path}=    Capture Page Screenshot    ${OUT}/none_ignored.png
    File Should Exist    ${path}

None Mode Multiple Screenshots Ignored
    [Documentation]    Multiple screenshots all ignored in trace
    Go To    https://www.google.com
    Capture Page Screenshot    ${OUT}/none_multi_1.png
    Capture Page Screenshot    ${OUT}/none_multi_2.png

None Mode Normal Logs Unaffected
    [Documentation]    Normal logging still works fine
    Log    This is a normal log message
    Go To    https://www.google.com
    Title Should Be    Google
