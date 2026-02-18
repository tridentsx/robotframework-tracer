# Test Configuration

## Running Tests Against Your OTel Endpoint

The test scripts read the endpoint from either:

### Option 1: Environment Variable (Recommended for CI/CD)

```bash
export OTEL_ENDPOINT=https://your-otel-endpoint.com
python3 test_centralized_otel.py
```

### Option 2: Local Config File (Recommended for Development)

Create a `.otel_config` file in the project root:

```bash
# Copy the example
cp .otel_config.example .otel_config

# Edit with your endpoint
echo "https://your-otel-endpoint.com" > .otel_config

# Run tests
python3 test_centralized_otel.py
```

**Note:** `.otel_config` is gitignored and won't be committed.

## Config File Format

The `.otel_config` file should contain just the base URL (one line):

```
https://your-otel-endpoint.com
```

The script will automatically append `/v1/traces`, `/v1/logs`, and `/v1/metrics` as needed.

## Examples

**With full path:**
```
https://otel.example.com/v1/traces
```

**With base URL (recommended):**
```
https://otel.example.com
```

Both work - the script normalizes the URL.

## Security

- Never commit `.otel_config` with real endpoints
- Use environment variables in CI/CD pipelines
- Keep internal endpoints private
