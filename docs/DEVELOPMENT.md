# Development Guide

## Setup Development Environment

### 1. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install package in development mode with dev dependencies
pip install -e ".[dev]"

# Or install from requirements files
pip install -r requirements-dev.txt
```

### 3. Verify Installation

```bash
# Check that the package is installed
pip list | grep robotframework-tracer

# Run tests to verify setup
pytest tests/unit/
```

## Running Tests

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/

# Run with coverage
pytest tests/unit/ --cov=src/robotframework_tracer --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py
```

### Integration Tests

```bash
# Run integration tests
pytest tests/integration/

# Run all tests
pytest
```

## Code Quality

### Format Code

```bash
# Format with black
black src/ tests/

# Or use make
make format
```

### Lint Code

```bash
# Run ruff
ruff check src/ tests/

# Run mypy
mypy src/

# Or use make
make lint
```

## Try the Example

### 1. Start Jaeger

```bash
cd examples
docker-compose up -d
```

### 2. Run Example Tests

```bash
# From repository root
robot --listener robotframework_tracer.TracingListener examples/example_test.robot
```

### 3. View Traces

Open http://localhost:16686 in your browser

### 4. Stop Jaeger

```bash
cd examples
docker-compose down
```

## Development Workflow

1. **Create virtual environment** (one time)
2. **Activate virtual environment** (each session)
3. **Make changes** to code
4. **Run tests** to verify
5. **Format and lint** before committing
6. **Deactivate** when done: `deactivate`

## Common Commands

```bash
# Activate venv
source venv/bin/activate

# Install/update dependencies
pip install -e ".[dev]"

# Run tests
make test

# Format code
make format

# Lint code
make lint

# Clean build artifacts
make clean

# Deactivate venv
deactivate
```

## Troubleshooting

### Virtual environment not found
```bash
# Make sure you created it
python3 -m venv venv
```

### Import errors
```bash
# Reinstall in development mode
pip install -e ".[dev]"
```

### Tests failing
```bash
# Make sure all dependencies are installed
pip install -r requirements-dev.txt
```
