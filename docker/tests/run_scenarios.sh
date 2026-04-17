#!/bin/bash
# Run all screenshot tracing scenarios with different configs.
# Each scenario uses its own config and produces its own trace output.
#
# Usage: docker compose run robot /tests/run_scenarios.sh

set -e

PASS=0
FAIL=0
TOTAL=0

run_scenario() {
    local name="$1"
    local config="$2"
    local test_file="$3"
    local output_dir="/output/${name}"
    TOTAL=$((TOTAL + 1))

    echo ""
    echo "============================================================"
    echo "  SCENARIO: ${name}"
    echo "  Config:   ${config}"
    echo "  Test:     ${test_file}"
    echo "============================================================"

    mkdir -p "${output_dir}"

    # Copy config to working directory so the tracer finds it
    cp "${config}" .rf-tracer.json

    if robot \
        --listener robotframework_tracer.TracingListener \
        --outputdir "${output_dir}" \
        --loglevel DEBUG \
        "${test_file}"; then
        PASS=$((PASS + 1))
        echo "  → PASS"
    else
        FAIL=$((FAIL + 1))
        echo "  → FAIL (check ${output_dir}/log.html)"
    fi
    echo ""
}

# Clean previous output
rm -rf /output/embedded /output/path /output/none /output/failure

# Scenario 1: Embedded mode (Selenium + headless Chrome)
# Screenshots should be base64-encoded in trace events
run_scenario "embedded" "/tests/configs/embedded.json" "/tests/01_embedded_mode.robot"

# Scenario 2: Path mode (Browser/Playwright + headless Chromium)
# Screenshots should have file path only, no base64 data
run_scenario "path" "/tests/configs/path.json" "/tests/02_path_mode.robot"

# Scenario 3: None mode (Selenium + headless Chrome)
# Screenshots taken but NOT present in trace at all
run_scenario "none" "/tests/configs/none.json" "/tests/03_none_mode.robot"

# Scenario 4: After keyword failure (Selenium + headless Chrome, embedded config)
# Screenshots captured in teardown / error handlers
run_scenario "failure" "/tests/configs/embedded.json" "/tests/04_after_keyword_failure.robot"

echo ""
echo "============================================================"
echo "  RESULTS: ${PASS}/${TOTAL} passed, ${FAIL} failed"
echo "============================================================"
echo ""
echo "Trace files:"
for f in /output/*/trace_*.json; do
    if [ -f "$f" ]; then
        size=$(wc -c < "$f")
        echo "  ${f} (${size} bytes)"
    fi
done
echo ""
echo "Verify with:"
echo "  python3 docker/verify_screenshots.py docker/output/embedded/trace_embedded.json --min-events 5"
echo "  python3 docker/verify_screenshots.py docker/output/path/trace_path.json --expect-path-only --min-events 3"
echo "  python3 docker/verify_screenshots.py docker/output/none/trace_none.json --expect-none"
echo "  python3 docker/verify_screenshots.py docker/output/failure/trace_embedded.json --min-events 2"
echo ""
echo "Jaeger UI: http://localhost:16686"
