"""
MailProbe-Py: A Python implementation of advanced Bayesian email classification and filtering.

This package provides a statistical email classifier that uses Bayesian analysis
to classify emails into multiple categories based on word frequency patterns.
It supports both traditional email classifiering and multi-category classification.

For easy integration into other scripts, use the high-level API:

    from mailprobe import MailProbeAPI

    # Create filter instance
    mail_filter = MailProbeAPI()

    # Train on messages
    mail_filter.train_good("path/to/good/emails")
    mail_filter.train_spam("path/to/spam/emails")

    # Classify new messages
    is_spam = mail_filter.classify("path/to/email.txt")

    # Or classify from string
    email_content = "From: test@example.com\\nSubject: Test\\n\\nHello"
    is_spam = mail_filter.classify_text(email_content)

For multi-category classification:

    from mailprobe import MultiCategoryFilter

    categories = ['work', 'personal', 'newsletters', 'spam']
    with MultiCategoryFilter(categories) as classifier:
        classifier.train_category('work', work_emails)
        result = classifier.classify(email_content)
        print(f"Category: {result.category}")

For convenience functions:

    from mailprobe import classify_email, get_spam_probability

    is_spam = classify_email(email_content)
    probability = get_spam_probability(email_content)
"""

__version__ = "0.1.0"
__author__ = "Peter Bowen"

# High-level API (recommended for integration)
from .api import (
    MailProbeAPI,
    BatchMailFilter,
    ClassificationResult,
    TrainingResult,
    classify_email,
    train_from_directories,
    get_spam_probability,
)

# Multi-category classification
from .multi_category import (
    MultiCategoryFilter,
    FolderBasedClassifier,
    CategoryResult,
    CategoryTrainingResult,
    classify_into_categories,
    train_from_folder_structure,
)

# Low-level components (for advanced usage)
from .filter import MailFilter, FilterConfig, MailScore
from .database import WordDatabase, WordData
from .tokenizer import EmailTokenizer, Token
from .message import EmailMessage, EmailMessageReader
from .config import MailProbeConfig, ConfigManager

# Utilities
from .utils import normalize_path, get_default_database_path, is_windows

__all__ = [
    # High-level API
    "MailProbeAPI",
    "BatchMailFilter",
    "ClassificationResult",
    "TrainingResult",
    "classify_email",
    "train_from_directories",
    "get_spam_probability",
    # Multi-category classification
    "MultiCategoryFilter",
    "FolderBasedClassifier",
    "CategoryResult",
    "CategoryTrainingResult",
    "classify_into_categories",
    "train_from_folder_structure",
    # Low-level components
    "MailFilter",
    "FilterConfig",
    "MailScore",
    "WordDatabase",
    "WordData",
    "EmailTokenizer",
    "Token",
    "EmailMessage",
    "EmailMessageReader",
    "MailProbeConfig",
    "ConfigManager",
    
    # Utilities
    "normalize_path",
    "get_default_database_path", 
    "is_windows",
]
