"""
Multi-category classification system for MailProbe-Py.

This module extends the basic spam/not-spam classification to support
multiple categories and corpuses, allowing for flexible email classification
into different folders or categories.
"""

import json
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .database import WordDatabase
from .filter import FilterConfig, MailFilter
from .message import EmailMessage, EmailMessageReader


@dataclass
class CategoryResult:
    """Result of multi-category classification."""

    category: str
    probability: float
    confidence: float
    all_scores: Dict[str, float]

    def __str__(self) -> str:
        return (
            f"{self.category} (prob={self.probability:.3f}, conf={self.confidence:.3f})"
        )


@dataclass
class CategoryTrainingResult:
    """Result of category training operation."""

    category: str
    messages_processed: int
    messages_updated: int
    database_updated: bool

    def __str__(self) -> str:
        return f"CategoryTrainingResult({self.category}: processed={self.messages_processed}, updated={self.messages_updated})"


class MultiCategoryFilter:
    """
    Multi-category email classifier.

    This class extends the basic email classifiering to support multiple categories,
    allowing emails to be classified into different folders or types beyond
    just spam/not-spam.

    Example:
        # Create multi-category filter
        categories = ['work', 'personal', 'newsletters', 'spam']
        classifier = MultiCategoryFilter(categories)

        # Train on different categories
        classifier.train_category('work', work_emails)
        classifier.train_category('personal', personal_emails)
        classifier.train_category('newsletters', newsletter_emails)
        classifier.train_category('spam', spam_emails)

        # Classify new email
        result = classifier.classify(new_email)
        print(f"Email should go to: {result.category}")
    """

    def __init__(
        self,
        categories: List[str],
        database_path: Optional[Union[str, Path]] = None,
        config: Optional[FilterConfig] = None,
    ):
        """
        Initialize multi-category filter.

        Args:
            categories: List of category names
            database_path: Path to database directory
            config: Filter configuration
        """
        self.categories = categories
        self.database_path = (
            Path(database_path)
            if database_path
            else Path.home() / ".mailprobe-py-multi"
        )
        self.config = config or FilterConfig()

        # Create separate filter for each category vs all others
        self.filters: Dict[str, MailFilter] = {}
        self.message_reader = EmailMessageReader()

        # Initialize filters for each category
        for category in categories:
            category_db_path = self.database_path / f"{category}_vs_others"
            self.filters[category] = MailFilter(category_db_path, self.config)

    def train_category(
        self,
        category: str,
        messages: Union[List[str], List[Path], List[EmailMessage], str, Path],
        force_update: bool = False,
    ) -> CategoryTrainingResult:
        """
        Train on messages for a specific category.

        Args:
            category: Category name to train
            messages: Messages to train on
            force_update: Force database update even if message was seen before

        Returns:
            CategoryTrainingResult with statistics
        """
        if category not in self.categories:
            raise ValueError(
                f"Unknown category: {category}. Available: {self.categories}"
            )

        # Convert messages to list of EmailMessage objects
        email_messages = self._get_messages_from_source(messages)

        processed = 0
        updated = 0

        # Train each filter
        for filter_category, spam_filter in self.filters.items():
            for message in email_messages:
                processed += 1
                # For the target category filter, train as "not spam" (positive)
                # For other category filters, train as "spam" (negative)
                is_spam = filter_category != category

                if spam_filter.train_message(message, is_spam, force_update):
                    updated += 1

        return CategoryTrainingResult(
            category=category,
            messages_processed=len(email_messages),
            messages_updated=updated,
            database_updated=updated > 0,
        )

    def classify(
        self,
        message_source: Union[str, Path, EmailMessage],
        return_all_scores: bool = False,
    ) -> CategoryResult:
        """
        Classify a message into one of the categories.

        Args:
            message_source: Message to classify
            return_all_scores: Include scores for all categories

        Returns:
            CategoryResult with classification
        """
        message = self._get_message(message_source)

        # Get scores from each category filter
        scores = {}
        for category, spam_filter in self.filters.items():
            score = spam_filter.score_message(message)
            # Convert spam probability to category probability
            # If spam_filter thinks it's "not spam", it belongs to this category
            category_prob = 1.0 - score.probability
            scores[category] = category_prob

        # Find the category with highest probability
        best_category = max(scores.keys(), key=lambda k: scores[k])
        best_prob = scores[best_category]

        # Calculate confidence as difference between best and second-best
        sorted_scores = sorted(scores.values(), reverse=True)
        confidence = (
            sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else 1.0
        )

        return CategoryResult(
            category=best_category,
            probability=best_prob,
            confidence=confidence,
            all_scores=scores if return_all_scores else {},
        )

    def get_category_stats(self, category: str) -> Dict[str, Any]:
        """
        Get statistics for a specific category.

        Args:
            category: Category name

        Returns:
            Dictionary with category statistics
        """
        if category not in self.categories:
            raise ValueError(f"Unknown category: {category}")

        return self.filters[category].get_database_info()

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all categories.

        Returns:
            Dictionary mapping category names to their statistics
        """
        return {
            category: self.get_category_stats(category) for category in self.categories
        }

    def cleanup_category(
        self, category: str, max_count: int = 2, max_age_days: int = 7
    ) -> int:
        """
        Clean up old/rare words for a specific category.

        Args:
            category: Category name
            max_count: Maximum total count for words to be removed
            max_age_days: Maximum age in days for words to be removed

        Returns:
            Number of words removed
        """
        if category not in self.categories:
            raise ValueError(f"Unknown category: {category}")

        return self.filters[category].cleanup_database(max_count, max_age_days)

    def cleanup_all_categories(
        self, max_count: int = 2, max_age_days: int = 7
    ) -> Dict[str, int]:
        """
        Clean up old/rare words for all categories.

        Args:
            max_count: Maximum total count for words to be removed
            max_age_days: Maximum age in days for words to be removed

        Returns:
            Dictionary mapping category names to number of words removed
        """
        results = {}
        for category in self.categories:
            results[category] = self.cleanup_category(category, max_count, max_age_days)
        return results

    def export_category(self, category: str) -> List[Tuple[str, int, int]]:
        """
        Export database contents for a specific category.

        Args:
            category: Category name

        Returns:
            List of (term, good_count, spam_count) tuples
        """
        if category not in self.categories:
            raise ValueError(f"Unknown category: {category}")

        return self.filters[category].export_database()

    def import_category(self, category: str, data: List[Tuple[str, int, int]]) -> int:
        """
        Import database contents for a specific category.

        Args:
            category: Category name
            data: List of (term, good_count, spam_count) tuples

        Returns:
            Number of words imported
        """
        if category not in self.categories:
            raise ValueError(f"Unknown category: {category}")

        return self.filters[category].import_database(data)

    def save_configuration(self, config_file: Union[str, Path]) -> None:
        """
        Save multi-category configuration to file.

        Args:
            config_file: Path to configuration file
        """
        config_data = {
            "categories": self.categories,
            "database_path": str(self.database_path),
            "filter_config": {
                "spam_threshold": self.config.spam_threshold,
                "min_word_count": self.config.min_word_count,
                "new_word_score": self.config.new_word_score,
                "terms_for_score": self.config.terms_for_score,
                "max_phrase_terms": self.config.max_phrase_terms,
                "min_term_length": self.config.min_term_length,
                "max_term_length": self.config.max_term_length,
                "remove_html": self.config.remove_html,
                "cache_size": self.config.cache_size,
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)

    @classmethod
    def load_configuration(cls, config_file: Union[str, Path]) -> "MultiCategoryFilter":
        """
        Load multi-category configuration from file.

        Args:
            config_file: Path to configuration file

        Returns:
            MultiCategoryFilter instance
        """
        with open(config_file, "r") as f:
            config_data = json.load(f)

        # Create FilterConfig from saved data
        filter_config = FilterConfig(**config_data["filter_config"])

        return cls(
            categories=config_data["categories"],
            database_path=config_data["database_path"],
            config=filter_config,
        )

    def close(self) -> None:
        """Close all category filters."""
        for spam_filter in self.filters.values():
            spam_filter.close()

    def _get_message(
        self, message_source: Union[str, Path, EmailMessage]
    ) -> EmailMessage:
        """Convert various message sources to EmailMessage."""
        if isinstance(message_source, EmailMessage):
            return message_source
        elif isinstance(message_source, (str, Path)):
            path = Path(message_source)
            if path.exists():
                # It's a file path
                messages = list(self.message_reader.read_from_file(path))
                if not messages:
                    raise ValueError(f"No messages found in {path}")
                return messages[0]
            else:
                # It's email content as string
                return EmailMessage(str(message_source))
        else:
            raise ValueError(f"Invalid message source type: {type(message_source)}")

    def _get_messages_from_source(
        self, source: Union[List[str], List[Path], List[EmailMessage], str, Path]
    ) -> List[EmailMessage]:
        """Get list of messages from various sources."""
        if isinstance(source, (str, Path)):
            # Single source
            path = Path(source)
            if path.exists():
                return list(self.message_reader.read_from_file(path))
            else:
                return [EmailMessage(str(source))]
        elif isinstance(source, list):
            # List of sources
            messages = []
            for item in source:
                if isinstance(item, EmailMessage):
                    messages.append(item)
                elif isinstance(item, (str, Path)):
                    path = Path(item)
                    if path.exists():
                        messages.extend(self.message_reader.read_from_file(path))
                    else:
                        messages.append(EmailMessage(str(item)))
            return messages
        else:
            raise ValueError(f"Invalid source type: {type(source)}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class FolderBasedClassifier:
    """
    Folder-based email classifier that automatically manages categories
    based on directory structure.

    This class provides a convenient way to train and classify emails
    based on folder organization, where each folder represents a category.

    Example:
        # Organize emails in folders:
        # emails/
        #   ├── work/
        #   ├── personal/
        #   ├── newsletters/
        #   └── spam/

        classifier = FolderBasedClassifier('emails/')
        classifier.train_from_folders()  # Auto-discover categories

        # Classify new email
        result = classifier.classify(new_email)
        print(f"Email should go to folder: {result.category}")
    """

    def __init__(
        self,
        base_path: Union[str, Path],
        database_path: Optional[Union[str, Path]] = None,
        config: Optional[FilterConfig] = None,
        exclude_folders: Optional[List[str]] = None,
    ):
        """
        Initialize folder-based classifier.

        Args:
            base_path: Base directory containing category folders
            database_path: Path to database directory
            config: Filter configuration
            exclude_folders: Folder names to exclude from categories
        """
        self.base_path = Path(base_path)
        self.exclude_folders = exclude_folders or [".git", ".DS_Store", "__pycache__"]

        # Auto-discover categories from folders
        self.categories = self._discover_categories()

        if not self.categories:
            raise ValueError(f"No valid category folders found in {base_path}")

        # Initialize multi-category filter
        self.classifier = MultiCategoryFilter(
            categories=self.categories, database_path=database_path, config=config
        )

    def _discover_categories(self) -> List[str]:
        """Discover categories from folder structure."""
        if not self.base_path.exists():
            raise ValueError(f"Base path does not exist: {self.base_path}")

        categories = []
        for item in self.base_path.iterdir():
            if (
                item.is_dir()
                and item.name not in self.exclude_folders
                and not item.name.startswith(".")
            ):
                categories.append(item.name)

        return sorted(categories)

    def train_from_folders(
        self, force_update: bool = False
    ) -> Dict[str, CategoryTrainingResult]:
        """
        Train classifier from all category folders.

        Args:
            force_update: Force database update even if message was seen before

        Returns:
            Dictionary mapping category names to training results
        """
        results = {}

        for category in self.categories:
            category_path = self.base_path / category
            if category_path.exists() and category_path.is_dir():
                # Get all email files in the category folder
                email_files: List[Path] = []
                for ext in ["*.txt", "*.eml", "*.msg"]:
                    email_files.extend(category_path.glob(ext))

                if email_files:
                    result = self.classifier.train_category(
                        category, email_files, force_update
                    )
                    results[category] = result

        return results

    def classify(
        self,
        message_source: Union[str, Path, EmailMessage],
        return_all_scores: bool = False,
    ) -> CategoryResult:
        """
        Classify a message into one of the folder categories.

        Args:
            message_source: Message to classify
            return_all_scores: Include scores for all categories

        Returns:
            CategoryResult with classification
        """
        return self.classifier.classify(message_source, return_all_scores)

    def get_folder_path(self, category: str) -> Path:
        """
        Get the folder path for a category.

        Args:
            category: Category name

        Returns:
            Path to category folder
        """
        return self.base_path / category

    def move_email_to_folder(self, email_file: Union[str, Path], category: str) -> Path:
        """
        Move an email file to the appropriate category folder.

        Args:
            email_file: Path to email file
            category: Target category

        Returns:
            New path of the moved file
        """
        email_path = Path(email_file)
        target_folder = self.get_folder_path(category)
        target_folder.mkdir(exist_ok=True)

        target_path = target_folder / email_path.name
        email_path.rename(target_path)

        return target_path

    def classify_and_move(
        self, email_file: Union[str, Path], confidence_threshold: float = 0.5
    ) -> Tuple[CategoryResult, Optional[Path]]:
        """
        Classify an email and optionally move it to the appropriate folder.

        Args:
            email_file: Path to email file
            confidence_threshold: Minimum confidence required to move file

        Returns:
            Tuple of (classification result, new path if moved)
        """
        result = self.classify(email_file, return_all_scores=True)

        moved_path = None
        if result.confidence >= confidence_threshold:
            moved_path = self.move_email_to_folder(email_file, result.category)

        return result, moved_path

    def get_categories(self) -> List[str]:
        """Get list of discovered categories."""
        return self.categories.copy()

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all categories."""
        return self.classifier.get_all_stats()

    def close(self) -> None:
        """Close the classifier."""
        self.classifier.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience functions for multi-category classification
def classify_into_categories(
    email_content: str,
    categories: List[str],
    database_path: Optional[Union[str, Path]] = None,
) -> CategoryResult:
    """
    Quick function to classify an email into multiple categories.

    Args:
        email_content: Raw email content
        categories: List of category names
        database_path: Optional database path

    Returns:
        CategoryResult with classification
    """
    with MultiCategoryFilter(categories, database_path) as classifier:
        return classifier.classify(email_content)


def train_from_folder_structure(
    base_path: Union[str, Path], database_path: Optional[Union[str, Path]] = None
) -> Dict[str, CategoryTrainingResult]:
    """
    Quick function to train from a folder structure.

    Args:
        base_path: Base directory containing category folders
        database_path: Optional database path

    Returns:
        Dictionary with training results for each category
    """
    with FolderBasedClassifier(base_path, database_path) as classifier:
        return classifier.train_from_folders()
