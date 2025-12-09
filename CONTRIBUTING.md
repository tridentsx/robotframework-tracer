# Contributing to Robot Framework Tracer

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd robotframework-tracer
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install in development mode**
```bash
pip install -e ".[dev]"
```

4. **Run tests**
```bash
pytest tests/unit/
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup instructions.

## How to Contribute

### Reporting Bugs

- Check if the bug has already been reported in Issues
- Include Robot Framework version, Python version, OS
- Provide minimal reproduction steps
- Include relevant logs and error messages

### Suggesting Features

- Check if the feature has been suggested
- Explain the use case and benefits
- Provide examples of how it would work

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Format code (`black src/ tests/`)
7. Lint code (`ruff check src/ tests/`)
8. Commit changes (`git commit -m 'Add amazing feature'`)
9. Push to branch (`git push origin feature/amazing-feature`)
10. Open a Pull Request

## Code Style

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use Ruff for linting
- Add type hints where appropriate
- Write docstrings for public APIs

## Testing

- Write unit tests for new features
- Maintain >70% code coverage
- Test with Robot Framework 6.0+
- Test on Python 3.8+

## Documentation

- Update README.md for user-facing changes
- Update docs/ for detailed documentation
- Add examples for new features
- Update CHANGELOG.md

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove)
- Reference issues when applicable

Examples:
- `Add log message capture feature`
- `Fix sampling configuration bug`
- `Update documentation for gRPC support`

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help others learn and grow

## Questions?

- Open an issue for questions
- Check existing documentation
- Ask in discussions

Thank you for contributing! 🎉
