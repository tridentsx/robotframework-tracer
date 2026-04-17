*** Settings ***
Documentation     Scenario: embedded mode — real browser screenshots base64-encoded in trace
...               Uses SeleniumLibrary with headless Chrome
Library           SeleniumLibrary
Library           OperatingSystem
Resource          selenium_setup.resource
Suite Setup       Open Headless Chrome    ${OUT}
Suite Teardown    Close All Browsers

*** Variables ***
${OUT}    /output/screenshots/embedded

*** Test Cases ***
Selenium PNG Screenshot
    [Documentation]    Default Capture Page Screenshot produces a PNG
    Go To    https://www.google.com
    ${path}=    Capture Page Screenshot    ${OUT}/selenium_basic.png
    File Should Exist    ${path}

Selenium JPEG Screenshot
    [Documentation]    Capture as JPEG to test format detection
    Go To    https://www.google.com
    ${path}=    Capture Page Screenshot    ${OUT}/selenium_format.jpg
    File Should Exist    ${path}

Selenium WebP Screenshot
    [Documentation]    Capture as WebP to test format detection
    Go To    https://www.google.com
    ${path}=    Capture Page Screenshot    ${OUT}/selenium_format.webp
    File Should Exist    ${path}

Selenium Multiple Screenshots In One Test
    [Documentation]    Multiple screenshots in a single test — all should be captured
    Go To    https://www.google.com
    Capture Page Screenshot    ${OUT}/selenium_multi_1.png
    Capture Page Screenshot    ${OUT}/selenium_multi_2.png
    Capture Page Screenshot    ${OUT}/selenium_multi_3.png

No Screenshot In Normal Log
    [Documentation]    Normal log messages should NOT produce screenshot events
    Log    Just a plain text message
    Log    <div>HTML but no img tag</div>    html=True
    Go To    https://www.google.com
    Title Should Be    Google
