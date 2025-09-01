# Contributing to MailProbe-Py

Thank you for your interest in contributing to MailProbe-Py! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mailprobe-py.git
   cd mailprobe-py
   ```

2. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**:
   ```bash
   poetry install --with dev
   ```

4. **Activate the virtual environment**:
   ```bash
   poetry shell
   ```

## Code Quality Standards

This project uses automated CI/CD to ensure code quality. All contributions must pass:

### Formatting and Style
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run these locally before submitting:
```bash
# Format code
poetry run black .
poetry run isort .

# Check formatting and linting
poetry run black --check .
poetry run isort --check-only .
poetry run flake8 src/ tests/
poetry run mypy src/mailprobe/
```

### Testing
- All tests must pass
- New features require tests
- Maintain or improve code coverage

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src/mailprobe --cov-report=term-missing
```

### Security
- **bandit** for security linting
- **safety** for dependency vulnerability checking

```bash
poetry run bandit -r src/
poetry run safety check
```

## Continuous Integration

Our GitHub Actions CI pipeline automatically:

1. **Code Quality Check**: Runs Black, isort, flake8, and mypy
2. **Cross-platform Testing**: Tests on Ubuntu, Windows, and macOS
3. **Multi-version Testing**: Tests Python 3.8-3.13
4. **Security Scanning**: Runs bandit and safety checks
5. **Package Building**: Verifies the package builds correctly

All checks must pass before a PR can be merged.

## Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code quality standards

3. **Add tests** for new functionality

4. **Update documentation** if needed

5. **Run the full test suite**:
   ```bash
   python run_tests.py all
   ```

6. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add feature: your feature description"
   ```

7. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request** on GitHub

## Code Style Guidelines

- Follow PEP 8 (enforced by flake8)
- Use type hints for all public APIs
- Write comprehensive docstrings
- Keep functions focused and small
- Use descriptive variable names
- Add comments for complex logic

## Testing Guidelines

- Write tests for all new features
- Use descriptive test names
- Test both success and failure cases
- Use fixtures for common test data
- Mock external dependencies

## Documentation

- Update README.md for user-facing changes
- Update docstrings for API changes
- Add examples for new features
- Update CHANGELOG.md for releases

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages (if any)

## Questions?

Feel free to open an issue for questions about contributing or reach out to the maintainers.

Thank you for contributing to MailProbe-Py! 🚀
