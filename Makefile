.PHONY: install test lint format clean help

help:
	@echo "Available commands:"
	@echo "  make install  - Install package in development mode"
	@echo "  make test     - Run tests with coverage"
	@echo "  make lint     - Run linters (ruff, mypy)"
	@echo "  make format   - Format code with black"
	@echo "  make clean    - Clean build artifacts"

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
