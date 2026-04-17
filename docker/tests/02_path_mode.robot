*** Settings ***
Documentation     Scenario: path mode — only file path reference in trace events
...               Uses Browser (Playwright) with headless Chromium
Library           Browser
Library           OperatingSystem

*** Variables ***
${OUT}    /output/screenshots/path

*** Test Cases ***
Browser PNG Screenshot Path Only
    [Documentation]    Screenshot captured but only path stored in trace (no base64)
    New Browser    chromium    headless=true
    New Page    https://www.google.com
    Create Directory    ${OUT}
    Take Screenshot    ${OUT}/browser_basic.png
    Close Browser

Browser Multiple Screenshots
    [Documentation]    Multiple screenshots all captured as path references
    New Browser    chromium    headless=true
    New Page    https://www.google.com
    Create Directory    ${OUT}
    Take Screenshot    ${OUT}/browser_multi_1.png
    Take Screenshot    ${OUT}/browser_multi_2.png
    Take Screenshot    ${OUT}/browser_multi_3.png
    Close Browser

Browser JPEG Screenshot
    [Documentation]    JPEG format via Playwright
    New Browser    chromium    headless=true
    New Page    https://www.google.com
    Create Directory    ${OUT}
    Take Screenshot    ${OUT}/browser_format.jpeg    fileType=jpeg
    Close Browser
