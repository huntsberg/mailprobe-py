# Development Guide

This guide covers development setup, testing, and contribution guidelines for MailProbe-Py.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Poetry (for dependency management)
- Git

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/mailprobe-py
   cd mailprobe-py
   ```

2. **Install dependencies**:
   ```bash
   poetry install --with dev
   ```

3. **Activate the virtual environment**:
   ```bash
   poetry shell
   ```

## Project Structure

```
mailprobe-py/
├── src/spamprobe/          # Main package source code
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration management
│   ├── database.py         # Word frequency database
│   ├── filter.py           # Main email classifier implementation
│   ├── message.py          # Email message parsing
│   └── tokenizer.py        # Email tokenization
├── tests/                  # Test suite
│   ├── test_filter.py      # Filter tests
│   ├── test_tokenizer.py   # Tokenizer tests
│   └── ...
├── pyproject.toml          # Poetry configuration
├── README.md               # Main documentation
├── USAGE.md                # Usage examples
└── DEVELOPMENT.md          # This file
```

## Development Workflow

### Running Tests

Run the full test suite:

```bash
poetry run pytest
```

Run tests with coverage:

```bash
poetry run pytest --cov=spamprobe --cov-report=html
```

Run specific test files:

```bash
poetry run pytest tests/test_filter.py -v
```

### Code Quality

Format code with Black:

```bash
poetry run black src/ tests/
```

Sort imports with isort:

```bash
poetry run isort src/ tests/
```

Check code style with flake8:

```bash
poetry run flake8 src/ tests/
```

Type checking with mypy:

```bash
poetry run mypy src/spamprobe/
```

Run all quality checks:

```bash
poetry run black src/ tests/
poetry run isort src/ tests/
poetry run flake8 src/ tests/
poetry run mypy src/spamprobe/
poetry run pytest
```

### Testing the CLI

Test CLI commands during development:

```bash
# Create test database
poetry run mailprobe-py -d ./test_db create-db

# Test with sample emails
echo "From: test@example.com
Subject: Test

This is a test message." | poetry run mailprobe-py -d ./test_db receive

# Check database info
poetry run mailprobe-py -d ./test_db info
```

## Architecture Overview

### Core Components

1. **EmailMessage** (`message.py`): Parses and represents email messages
2. **EmailTokenizer** (`tokenizer.py`): Extracts words and phrases from emails
3. **WordDatabase** (`database.py`): Stores and retrieves word frequency data
4. **MailFilter** (`filter.py`): Main filter logic using Bayesian analysis
5. **CLI** (`cli.py`): Command-line interface

### Data Flow

```
Email Input → EmailMessage → EmailTokenizer → Tokens → MailFilter → Score
                                                    ↓
                                              WordDatabase
```

### Key Algorithms

1. **Tokenization**: Extracts words and phrases from email headers and body
2. **Bayesian Scoring**: Calculates spam probability using word frequencies
3. **Token Selection**: Chooses most significant tokens for scoring
4. **Database Management**: Efficient storage and retrieval of word data

## Adding New Features

### Adding a New Command

1. **Add command function** in `cli.py`:
   ```python
   @cli.command()
   @click.argument('files', nargs=-1, type=click.Path(exists=True))
   @click.pass_context
   def my_command(ctx, files):
       """My new command description."""
       config = ctx.obj['config']
       # Implementation here
   ```

2. **Add tests** in `tests/test_cli.py`:
   ```python
   def test_my_command():
       # Test implementation
       pass
   ```

### Adding Configuration Options

1. **Update FilterConfig** in `filter.py`:
   ```python
   @dataclass
   class FilterConfig:
       # ... existing fields ...
       my_new_option: bool = False
   ```

2. **Update CLI options** in `cli.py`:
   ```python
   @click.option('--my-option', is_flag=True, help='My new option')
   ```

3. **Update configuration management** in `config.py`

### Adding New Tokenization Features

1. **Extend EmailTokenizer** in `tokenizer.py`
2. **Add corresponding tests** in `tests/test_tokenizer.py`
3. **Update documentation**

## Testing Guidelines

### Test Categories

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **CLI Tests**: Test command-line interface
4. **Performance Tests**: Test with large datasets

### Writing Tests

Use pytest conventions:

```python
class TestMyFeature:
    def setup_method(self):
        """Set up test fixtures."""
        pass
    
    def test_basic_functionality(self):
        """Test basic feature functionality."""
        # Arrange
        # Act
        # Assert
        pass
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        pass
```

### Test Data

- Use realistic email samples
- Test with various email formats (mbox, maildir, single messages)
- Include edge cases (empty messages, malformed headers, etc.)

## Performance Considerations

### Database Performance

- Use appropriate cache sizes for your use case
- Regular cleanup of old/rare terms
- Consider database file location (local vs. network storage)

### Memory Usage

- Monitor memory usage with large datasets
- Adjust cache sizes based on available memory
- Use generators for processing large mailboxes

### Profiling

Profile performance-critical code:

```python
import cProfile
import pstats

# Profile a function
cProfile.run('my_function()', 'profile_output')
stats = pstats.Stats('profile_output')
stats.sort_stats('cumulative').print_stats(10)
```

## Debugging

### Common Issues

1. **Database corruption**: Use export/import to recover
2. **Poor accuracy**: Check training data balance
3. **Memory issues**: Adjust cache sizes
4. **Performance problems**: Profile and optimize hot paths

### Debug Mode

Enable debug output:

```bash
poetry run mailprobe-py --debug score < email.txt
```

### Logging

Add logging for debugging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
```

## Contributing

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make changes** following coding standards
4. **Add tests** for new functionality
5. **Run quality checks**: `poetry run pytest && poetry run black src/ tests/`
6. **Update documentation** as needed
7. **Submit pull request**

### Coding Standards

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small
- Use meaningful variable and function names

### Documentation

- Update README.md for user-facing changes
- Update USAGE.md for new commands or options
- Add docstrings for new functions and classes
- Include examples in documentation

## Release Process

### Version Management

Update version in `pyproject.toml`:

```toml
[tool.poetry]
version = "0.2.0"
```

### Building and Publishing

```bash
# Build package
poetry build

# Publish to PyPI (requires authentication)
poetry publish
```

### Release Checklist

- [ ] Update version number
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create git tag
- [ ] Build and publish package
- [ ] Create GitHub release

## Troubleshooting

### Common Development Issues

1. **Import errors**: Check PYTHONPATH and package structure
2. **Test failures**: Ensure clean test environment
3. **Poetry issues**: Try `poetry install --no-cache`
4. **Type checking errors**: Update type hints

### Getting Help

- Check existing issues on GitHub
- Review documentation and examples
- Ask questions in discussions
- Submit bug reports with minimal reproduction cases
