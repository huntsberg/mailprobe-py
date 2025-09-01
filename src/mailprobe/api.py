"""
High-level object-oriented API for MailProbe-Py.

This module provides a clean, easy-to-use interface for integrating
MailProbe-Py into other applications and scripts.
"""

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .config import ConfigManager, MailProbeConfig
from .database import WordDatabase
from .filter import FilterConfig, MailFilter, MailScore
from .message import EmailMessage, EmailMessageReader
from .utils import get_default_database_path, normalize_path


@dataclass
class TrainingResult:
    """Result of training operation."""

    messages_processed: int
    messages_updated: int
    database_updated: bool

    def __str__(self) -> str:
        return f"TrainingResult(processed={self.messages_processed}, updated={self.messages_updated})"


@dataclass
class ClassificationResult:
    """Result of message classification."""

    is_spam: bool
    probability: float
    confidence: float
    terms_used: int
    digest: str
    top_terms: List[Tuple[str, float, int]]

    def __str__(self) -> str:
        status = "SPAM" if self.is_spam else "GOOD"
        return f"{status} (prob={self.probability:.3f}, conf={self.confidence:.3f})"


class MailProbeAPI:
    """
    High-level API for MailProbe email classification and filtering.

    This class provides a simple, object-oriented interface for email classification
    operations. It handles database management, configuration, and provides
    convenient methods for common operations including email classifiering and
    multi-category classification.

    Example:
        # Basic usage
        mail_filter = MailProbeAPI()

        # Train on messages
        mail_filter.train_good("path/to/good/emails")
        mail_filter.train_spam("path/to/spam/emails")

        # Classify new messages
        result = mail_filter.classify("path/to/new/email.txt")
        print(f"Is spam: {result.is_spam}, Probability: {result.probability}")

        # Or classify from string
        email_content = "From: test@example.com\\nSubject: Test\\n\\nHello world"
        result = mail_filter.classify_text(email_content)
    """

    def __init__(
        self,
        database_path: Optional[Union[str, Path]] = None,
        config: Optional[Union[MailProbeConfig, FilterConfig, Dict[str, Any]]] = None,
        auto_create: bool = True,
    ):
        """
        Initialize MailProbe API.

        Args:
            database_path: Path to database directory (default: ~/.mailprobe-py)
            config: Configuration object or dictionary
            auto_create: Automatically create database if it doesn't exist
        """
        # Set up database path
        if database_path is None:
            self.database_path = get_default_database_path()
        else:
            self.database_path = normalize_path(database_path)

        # Handle configuration
        if config is None:
            self.config = FilterConfig()
        elif isinstance(config, dict):
            self.config = FilterConfig(**config)
        elif isinstance(config, MailProbeConfig):
            self.config = config.to_filter_config()
        elif isinstance(config, FilterConfig):
            self.config = config
        else:
            raise ValueError(f"Invalid config type: {type(config)}")

        # Create database directory if needed
        if auto_create:
            self.database_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self._filter: Optional[MailFilter] = None
        self._message_reader = EmailMessageReader()

    @property
    def filter(self) -> MailFilter:
        """Get the mail filter instance (lazy initialization)."""
        if self._filter is None:
            self._filter = MailFilter(self.database_path, self.config)
        return self._filter

    def classify(
        self,
        message_source: Union[str, Path, EmailMessage],
        return_details: bool = False,
    ) -> Union[bool, ClassificationResult]:
        """
        Classify a message as spam or not spam.

        Args:
            message_source: Path to email file, EmailMessage object, or email content string
            return_details: If True, return detailed ClassificationResult

        Returns:
            bool (is_spam) if return_details=False, ClassificationResult otherwise
        """
        message = self._get_message(message_source)
        score = self.filter.score_message(message)

        if return_details:
            return ClassificationResult(
                is_spam=score.is_spam,
                probability=score.probability,
                confidence=score.confidence,
                terms_used=score.terms_used,
                digest=message.digest,
                top_terms=score.top_terms,
            )
        else:
            return score.is_spam

    def classify_text(
        self, email_content: str, return_details: bool = False
    ) -> Union[bool, ClassificationResult]:
        """
        Classify email content as spam or not spam.

        Args:
            email_content: Raw email message content
            return_details: If True, return detailed ClassificationResult

        Returns:
            bool (is_spam) if return_details=False, ClassificationResult otherwise
        """
        message = EmailMessage(email_content)
        return self.classify(message, return_details)

    def get_spam_probability(
        self, message_source: Union[str, Path, EmailMessage]
    ) -> float:
        """
        Get spam probability for a message.

        Args:
            message_source: Path to email file, EmailMessage object, or email content string

        Returns:
            Spam probability (0.0 to 1.0)
        """
        message = self._get_message(message_source)
        score = self.filter.score_message(message)
        return score.probability

    def train_good(
        self,
        source: Union[str, Path, List[Union[str, Path]]],
        force_update: bool = False,
    ) -> TrainingResult:
        """
        Train the filter on good (non-spam) messages.

        Args:
            source: Path to email file/directory, or list of paths
            force_update: Force database update even if message was seen before

        Returns:
            TrainingResult with statistics
        """
        return self._train_messages(source, is_spam=False, force_update=force_update)

    def train_spam(
        self,
        source: Union[str, Path, List[Union[str, Path]]],
        force_update: bool = False,
    ) -> TrainingResult:
        """
        Train the filter on spam messages.

        Args:
            source: Path to email file/directory, or list of paths
            force_update: Force database update even if message was seen before

        Returns:
            TrainingResult with statistics
        """
        return self._train_messages(source, is_spam=True, force_update=force_update)

    def train_message(
        self,
        message_source: Union[str, Path, EmailMessage],
        is_spam: bool,
        force_update: bool = False,
    ) -> bool:
        """
        Train on a single message.

        Args:
            message_source: Path to email file, EmailMessage object, or email content string
            is_spam: Whether the message is spam
            force_update: Force database update even if message was seen before

        Returns:
            True if database was updated
        """
        message = self._get_message(message_source)
        return self.filter.train_message(message, is_spam, force_update)

    def train_selective(
        self, source: Union[str, Path, List[Union[str, Path]]], is_spam: bool
    ) -> TrainingResult:
        """
        Train selectively (only on difficult messages).

        Args:
            source: Path to email file/directory, or list of paths
            is_spam: Whether the messages are spam

        Returns:
            TrainingResult with statistics
        """
        messages = self._get_messages_from_source(source)
        processed = 0
        updated = 0

        for message in messages:
            processed += 1
            if self.filter.train_message_selective(message, is_spam):
                updated += 1

        return TrainingResult(
            messages_processed=processed,
            messages_updated=updated,
            database_updated=updated > 0,
        )

    def remove_message(self, message_source: Union[str, Path, EmailMessage]) -> bool:
        """
        Remove a message from the database.

        Args:
            message_source: Path to email file, EmailMessage object, or email content string

        Returns:
            True if message was found and removed
        """
        message = self._get_message(message_source)
        return self.filter.remove_message(message)

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with database information
        """
        return self.filter.get_database_info()

    def cleanup_database(self, max_count: int = 2, max_age_days: int = 7) -> int:
        """
        Clean up old/rare words from database.

        Args:
            max_count: Maximum total count for words to be removed
            max_age_days: Maximum age in days for words to be removed

        Returns:
            Number of words removed
        """
        return self.filter.cleanup_database(max_count, max_age_days)

    def export_database(self) -> List[Tuple[str, int, int]]:
        """
        Export database contents.

        Returns:
            List of (term, good_count, spam_count) tuples
        """
        return self.filter.export_database()

    def import_database(self, data: List[Tuple[str, int, int]]) -> int:
        """
        Import database contents.

        Args:
            data: List of (term, good_count, spam_count) tuples

        Returns:
            Number of words imported
        """
        return self.filter.import_database(data)

    def backup_database(self, backup_path: Union[str, Path]) -> None:
        """
        Create a backup of the database.

        Args:
            backup_path: Path where to save the backup
        """
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Export data and save as CSV
        data = self.export_database()

        with open(backup_path, "w") as f:
            f.write("term,good_count,spam_count\n")
            for term, good_count, spam_count in data:
                f.write(f'"{term}",{good_count},{spam_count}\n')

    def restore_database(self, backup_path: Union[str, Path]) -> int:
        """
        Restore database from backup.

        Args:
            backup_path: Path to backup file

        Returns:
            Number of words imported
        """
        import csv

        backup_path = Path(backup_path)
        data = []

        with open(backup_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header

            for row in reader:
                if len(row) >= 3:
                    term = row[0].strip('"')
                    good_count = int(row[1])
                    spam_count = int(row[2])
                    data.append((term, good_count, spam_count))

        return self.import_database(data)

    def reset_database(self) -> None:
        """Reset the database (remove all data)."""
        if self._filter:
            self._filter.close()
            self._filter = None

        # Remove database files
        db_file = self.database_path / "words.db"
        if db_file.exists():
            db_file.unlink()

    def close(self) -> None:
        """Close the email classifier and database connections."""
        if self._filter:
            self._filter.close()
            self._filter = None

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
                messages = list(self._message_reader.read_from_file(path))
                if not messages:
                    raise ValueError(f"No messages found in {path}")
                return messages[0]  # Return first message
            else:
                # It's email content as string
                return EmailMessage(str(message_source))
        else:
            raise ValueError(f"Invalid message source type: {type(message_source)}")

    def _get_messages_from_source(
        self, source: Union[str, Path, List[Union[str, Path]]]
    ) -> List[EmailMessage]:
        """Get list of messages from various sources."""
        if isinstance(source, (str, Path)):
            sources = [source]
        else:
            sources = source

        messages = []
        for src in sources:
            path = Path(src)
            if path.exists():
                messages.extend(self._message_reader.read_from_file(path))
            else:
                # Treat as email content
                messages.append(EmailMessage(str(src)))

        return messages

    def _train_messages(
        self,
        source: Union[str, Path, List[Union[str, Path]]],
        is_spam: bool,
        force_update: bool = False,
    ) -> TrainingResult:
        """Train on multiple messages."""
        messages = self._get_messages_from_source(source)
        processed = 0
        updated = 0

        for message in messages:
            processed += 1
            if self.filter.train_message(message, is_spam, force_update):
                updated += 1

        return TrainingResult(
            messages_processed=processed,
            messages_updated=updated,
            database_updated=updated > 0,
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class BatchMailFilter:
    """
    Batch processing mail filter for handling large volumes of email.

    This class is optimized for processing many emails efficiently,
    with features like batch training and parallel processing.
    """

    def __init__(self, api: MailProbeAPI):
        """
        Initialize batch filter.

        Args:
            api: MailProbeAPI instance to use
        """
        self.api = api

    def classify_batch(
        self, sources: List[Union[str, Path]], return_details: bool = False
    ) -> List[Union[bool, ClassificationResult]]:
        """
        Classify multiple messages in batch.

        Args:
            sources: List of message sources (paths or content)
            return_details: If True, return detailed results

        Returns:
            List of classification results
        """
        results = []
        for source in sources:
            try:
                result = self.api.classify(source, return_details)
                results.append(result)
            except Exception as e:
                # Handle individual failures gracefully
                if return_details:
                    results.append(
                        ClassificationResult(
                            is_spam=False,
                            probability=0.5,
                            confidence=0.0,
                            terms_used=0,
                            digest="",
                            top_terms=[],
                        )
                    )
                else:
                    results.append(False)

        return results

    def train_batch(
        self,
        good_sources: List[Union[str, Path]] = None,
        spam_sources: List[Union[str, Path]] = None,
        selective: bool = False,
    ) -> Dict[str, TrainingResult]:
        """
        Train on multiple message sources in batch.

        Args:
            good_sources: List of good message sources
            spam_sources: List of spam message sources
            selective: Use selective training mode

        Returns:
            Dictionary with training results for 'good' and 'spam'
        """
        results = {}

        if good_sources:
            if selective:
                results["good"] = self.api.train_selective(good_sources, is_spam=False)
            else:
                results["good"] = self.api.train_good(good_sources)

        if spam_sources:
            if selective:
                results["spam"] = self.api.train_selective(spam_sources, is_spam=True)
            else:
                results["spam"] = self.api.train_spam(spam_sources)

        return results


# Convenience functions for quick usage
def classify_email(
    email_content: str, database_path: Optional[Union[str, Path]] = None
) -> bool:
    """
    Quick function to classify an email.

    Args:
        email_content: Raw email content
        database_path: Optional database path

    Returns:
        True if spam, False if not spam
    """
    with MailProbeAPI(database_path) as api:
        return api.classify_text(email_content)


def train_from_directories(
    good_dir: Union[str, Path],
    spam_dir: Union[str, Path],
    database_path: Optional[Union[str, Path]] = None,
) -> Dict[str, TrainingResult]:
    """
    Quick function to train from directories of emails.

    Args:
        good_dir: Directory containing good emails
        spam_dir: Directory containing spam emails
        database_path: Optional database path

    Returns:
        Dictionary with training results
    """
    with MailProbeAPI(database_path) as api:
        good_files = list(Path(good_dir).glob("*"))
        spam_files = list(Path(spam_dir).glob("*"))

        batch_filter = BatchMailFilter(api)
        return batch_filter.train_batch(good_files, spam_files)


def get_spam_probability(
    email_content: str, database_path: Optional[Union[str, Path]] = None
) -> float:
    """
    Quick function to get spam probability.

    Args:
        email_content: Raw email content
        database_path: Optional database path

    Returns:
        Spam probability (0.0 to 1.0)
    """
    with MailProbeAPI(database_path) as api:
        return api.get_spam_probability(email_content)
