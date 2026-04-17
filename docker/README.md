# Docker Test Environment

Run real Robot Framework tests with SeleniumLibrary (Chrome) and Browser (Playwright) to verify screenshot tracing end-to-end.

## Quick Start

```bash
cd docker

# Build image and run all scenarios
docker compose up --build

# Verify trace output
python3 verify_screenshots.py output/embedded/trace_embedded.json --min-events 5
python3 verify_screenshots.py output/path/trace_path.json --expect-path-only --min-events 3
python3 verify_screenshots.py output/none/trace_none.json --expect-none
python3 verify_screenshots.py output/failure/trace_embedded.json --min-events 2

# View traces in Jaeger UI
open http://localhost:16686
```

## Scenarios

| # | Name | Library | Config | What it tests |
|---|------|---------|--------|---------------|
| 01 | Embedded mode | SeleniumLibrary | `embedded.json` | PNG/JPEG/WebP screenshots base64-encoded in trace events |
| 02 | Path mode | Browser (Playwright) | `path.json` | File path reference only, no binary data |
| 03 | None mode | SeleniumLibrary | `none.json` | Screenshots taken but NOT in trace |
| 04 | Failure handler | SeleniumLibrary | `embedded.json` | Screenshots in teardown / error recovery |

## Volumes

| Host path | Container path | Purpose |
|-----------|---------------|---------|
| `docker/tests/` | `/tests` | Input: .robot files, configs |
| `docker/output/` | `/output` | Output: RF reports, trace JSON, screenshots |

## Run a Single Scenario

```bash
# Copy the config you want, then run
docker compose run robot bash -c "cp /tests/configs/embedded.json .rf-tracer.json && robot --listener robotframework_tracer.TracingListener --outputdir /output /tests/01_embedded_mode.robot"
```

## Cleanup

```bash
docker compose down
rm -rf output/
```
