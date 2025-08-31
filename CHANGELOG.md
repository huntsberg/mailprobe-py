# Changelog

All notable changes to MailProbe-Py will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Performance optimizations for large datasets
- Additional configuration presets
- Email client integration examples
- Machine learning enhancements

## [0.1.0] - 2024-01-31

### Added

#### Core Spam Filtering Engine
- **Bayesian email classifier** implementation based on original MailProbe
- **Statistical analysis** using word frequency patterns
- **Adaptive learning** from good and spam message training
- **Message digest tracking** to prevent duplicate processing
- **Configurable spam threshold** and scoring parameters

#### Email Processing
- **EmailMessage class** for parsing raw email content
- **Header extraction** with case-insensitive access
- **Body content processing** with MIME support
- **Message digest calculation** using MD5 hashing
- **EmailMessageReader** for file and directory processing
- **Mbox and Maildir format support**

#### Text Tokenization
- **EmailTokenizer** for extracting words and phrases from emails
- **HTML tag removal** and content extraction
- **URL detection and tokenization**
- **Header-specific token prefixes** (from:, subject:, etc.)
- **Multi-word phrase generation** (configurable length)
- **Non-ASCII character replacement**
- **Term length filtering** (min/max length limits)
- **Punctuation and whitespace handling**

#### Database Management
- **SQLite-based word frequency database**
- **WordData class** for individual word statistics
- **Efficient caching** with configurable cache size
- **Message count tracking** (good vs spam)
- **Database cleanup operations** for old/rare words
- **Export/import functionality** for database migration
- **Vacuum operations** for database optimization
- **Concurrent access handling**

#### High-Level Object-Oriented API
- **MailProbeAPI class** for easy integration
- **Context manager support** (`with` statement)
- **Batch processing** with BatchMailFilter
- **Classification methods** (simple boolean and detailed results)
- **Training methods** (good, spam, selective training)
- **Database operations** (backup, restore, cleanup)
- **Configuration management** with multiple input formats
- **Result objects** (ClassificationResult, TrainingResult)

#### Convenience Functions
- **classify_email()** - Quick email classification
- **get_spam_probability()** - Get spam probability score
- **train_from_directories()** - Batch training from directories

#### Command-Line Interface
- **Complete CLI implementation** using Click framework
- **Database management commands**:
  - `create-db` - Initialize new database
  - `info` - Display database statistics
  - `cleanup` - Remove old/rare words
  - `purge` - Remove words below threshold
- **Training commands**:
  - `good` - Train on good (non-spam) messages
  - `spam` - Train on spam messages
  - `train` - Selective training mode
- **Classification commands**:
  - `score` - Score individual messages
  - `receive` - Process incoming messages
- **Utility commands**:
  - `dump` - Export database contents
  - `import-db` - Import database contents
  - `remove` - Remove specific messages
- **Configuration options**:
  - Spam threshold adjustment
  - Cache size configuration
  - Tokenizer parameters
  - Verbose output mode

#### Configuration System
- **Hierarchical configuration** with multiple classes:
  - DatabaseConfig - Database settings
  - TokenizerConfig - Text processing settings
  - ScoringConfig - Spam scoring parameters
  - MailProbeConfig - Master configuration
- **Configuration presets**:
  - `graham` - Paul Graham's original algorithm settings
  - `conservative` - Lower false positive rate
  - `aggressive` - Higher spam detection rate
- **JSON configuration files** with automatic loading/saving
- **Command-line argument integration**
- **Environment variable support**
- **Configuration validation** and error handling

#### Package Management
- **Poetry-based** dependency and environment management
- **pyproject.toml** configuration for modern Python packaging
- **Development dependencies** included (testing, linting, formatting)
- **Entry point scripts** for CLI access
- **Proper package structure** with src/ layout

#### Comprehensive Test Suite
- **97 test cases** covering all functionality
- **81% code coverage** across all modules
- **Test categories**:
  - API tests (19 tests) - High-level interface
  - CLI tests (13 tests) - Command-line functionality
  - Config tests (15 tests) - Configuration management
  - Database tests (14 tests) - Data storage operations
  - Filter tests (12 tests) - Core filtering logic
  - Message tests (12 tests) - Email parsing
  - Tokenizer tests (11 tests) - Text processing
  - Integration test (1 test) - End-to-end workflow
- **Test infrastructure**:
  - Pytest framework with fixtures
  - Temporary test environments
  - Automatic cleanup
  - Coverage reporting (HTML and terminal)
  - Click testing for CLI validation
- **Convenient test runner** (`run_tests.py`) with multiple options

#### Documentation
- **Comprehensive README** with installation and usage examples
- **Object-Oriented API Guide** (OO_API_GUIDE.md) with detailed examples
- **Usage Guide** (USAGE.md) with CLI commands and integration
- **Development Guide** (DEVELOPMENT.md) for contributors
- **Test Summary** (TEST_SUMMARY.md) with detailed test documentation
- **Integration examples** showing real-world usage patterns
- **Docstrings** throughout codebase for API documentation

#### Integration Examples
- **Basic usage patterns** for quick start
- **Advanced integration** with custom email processors
- **Batch processing** for high-volume scenarios
- **Email server integration** patterns
- **User feedback learning** systems
- **Whitelisting and custom rules** examples
- **Performance optimization** techniques

### Technical Features

#### Algorithm Implementation
- **Bayesian probability calculation** with configurable parameters
- **Word frequency analysis** with good/spam count tracking
- **Selective training** to focus on difficult messages
- **Confidence scoring** for classification reliability
- **Top terms analysis** for spam detection insights
- **Message reclassification** support

#### Performance Optimizations
- **SQLite database** with indexing for fast lookups
- **Word caching** to reduce database queries
- **Batch operations** for processing multiple messages
- **Efficient tokenization** with configurable limits
- **Memory management** with configurable cache sizes
- **Database vacuum** operations for maintenance

#### Error Handling
- **Graceful degradation** for malformed emails
- **Database corruption recovery** mechanisms
- **Invalid input validation** throughout
- **Comprehensive error messages** for debugging
- **Logging support** with configurable verbosity
- **Exception handling** in all critical paths

#### Security Considerations
- **Input sanitization** for email content
- **Path validation** for file operations
- **SQL injection prevention** with parameterized queries
- **Temporary file handling** with proper cleanup
- **Permission checking** for database operations

#### Compatibility
- **Python 3.8+** support
- **Cross-platform** compatibility (Windows, macOS, Linux)
- **Unicode handling** for international emails
- **Various email formats** (mbox, Maildir, individual files)
- **Configurable character encoding** handling

### Development Infrastructure

#### Code Quality
- **Black** code formatting with consistent style
- **isort** import sorting for clean organization
- **flake8** linting for code quality checks
- **mypy** type checking for better reliability
- **Comprehensive docstrings** for all public APIs

#### Project Structure
- **src/ layout** for proper package organization
- **Modular design** with clear separation of concerns
- **Clean interfaces** between components
- **Extensible architecture** for future enhancements
- **Standard Python packaging** practices

#### Version Control
- **Git-friendly** structure with proper .gitignore
- **Semantic versioning** for releases
- **Changelog maintenance** for tracking changes
- **Branch-friendly** development workflow

## [0.0.1] - 2024-01-30

### Added
- Initial project structure
- Basic email classifiering concept
- Poetry configuration setup

---

## Version History Summary

- **v0.1.0** (2024-01-31): Complete implementation with comprehensive features
- **v0.0.1** (2024-01-30): Initial project setup

## Migration Notes

### From Original MailProbe (C++)

MailProbe-Py maintains compatibility with the original MailProbe's core algorithm while providing:

- **Modern Python API** for easy integration
- **Object-oriented design** for better maintainability  
- **Comprehensive test coverage** for reliability
- **Enhanced configuration** system with presets
- **Better documentation** and examples
- **Package manager integration** with Poetry

### Database Compatibility

- Uses SQLite instead of Berkeley DB for better Python integration
- Maintains same statistical approach and word frequency tracking
- Provides export/import tools for data migration
- Compatible scoring algorithms with original implementation

### API Evolution

The API has been designed for:
- **Backward compatibility** with future versions
- **Extensibility** for new features
- **Performance** optimizations
- **Ease of use** for integration

## Contributing

See [DEVELOPMENT.md](DEVELOPMENT.md) for information about contributing to MailProbe-Py.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Original MailProbe by Burton Computer Corporation
- Paul Graham's "A Plan for Spam" article
- The Python community for excellent libraries and tools
