*** Settings ***
Library    SeleniumLibrary
Library    OperatingSystem

*** Keywords ***
Open Headless Chrome
    [Arguments]    ${output_dir}=/output/screenshots
    Create Directory    ${output_dir}
    Open Browser    about:blank    Chrome
    ...    options=add_argument("--headless=new");add_argument("--no-sandbox");add_argument("--disable-dev-shm-usage");add_argument("--disable-gpu");add_argument("--window-size=1280,720")
