"""Tests for the high-level API."""

import pytest
import tempfile
from pathlib import Path

from mailprobe.api import (
    MailProbeAPI,
    BatchMailFilter,
    ClassificationResult,
    TrainingResult,
    classify_email,
    get_spam_probability,
    train_from_directories,
)
from mailprobe.message import EmailMessage


class TestMailProbeAPI:
    """Test cases for MailProbeAPI."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir)
        self.api = MailProbeAPI(self.db_path)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.api.close()
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_api_initialization(self):
        """Test API initialization."""
        assert self.api.database_path == self.db_path
        assert self.api.config is not None

        # Database should be created
        db_file = self.db_path / "words.db"
        # Access filter to trigger database creation
        _ = self.api.filter
        assert db_file.exists()

    def test_classify_text_basic(self):
        """Test basic text classification."""
        email_content = """From: test@example.com
Subject: Test message

This is a test message.
"""

        # Should return boolean by default
        result = self.api.classify_text(email_content)
        assert isinstance(result, bool)

        # Should return detailed result when requested
        detailed = self.api.classify_text(email_content, return_details=True)
        assert isinstance(detailed, ClassificationResult)
        assert isinstance(detailed.is_spam, bool)
        assert 0.0 <= detailed.probability <= 1.0
        assert 0.0 <= detailed.confidence <= 1.0

    def test_classify_message_object(self):
        """Test classification with EmailMessage object."""
        message = EmailMessage(
            """From: test@example.com
Subject: Test

Hello world!
"""
        )

        result = self.api.classify(message)
        assert isinstance(result, bool)

    def test_get_spam_probability(self):
        """Test getting spam probability."""
        email_content = """From: test@example.com
Subject: Test

Hello world!
"""

        prob = self.api.get_spam_probability(email_content)
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

    def test_train_message(self):
        """Test training on individual messages."""
        email_content = """From: friend@example.com
Subject: Meeting

Let's meet for lunch tomorrow.
"""

        # Train as good message
        updated = self.api.train_message(email_content, is_spam=False)
        assert isinstance(updated, bool)

        # Check database stats
        stats = self.api.get_database_stats()
        assert stats["good_message_count"] >= 1

    def test_train_good_and_spam(self):
        """Test training on good and spam messages."""
        good_content = """From: friend@example.com
Subject: Lunch meeting

Let's meet for lunch tomorrow at noon.
"""

        spam_content = """From: spammer@badsite.com
Subject: FREE MONEY NOW!!!

Click here to get FREE MONEY! Limited time offer!
"""

        # Train on good message
        good_result = self.api.train_good([good_content])
        assert isinstance(good_result, TrainingResult)
        assert good_result.messages_processed >= 1

        # Train on spam message
        spam_result = self.api.train_spam([spam_content])
        assert isinstance(spam_result, TrainingResult)
        assert spam_result.messages_processed >= 1

        # Check database stats
        stats = self.api.get_database_stats()
        assert stats["good_message_count"] >= 1
        assert stats["spam_message_count"] >= 1

    def test_selective_training(self):
        """Test selective training mode."""
        email_content = """From: test@example.com
Subject: Test

This is a test message.
"""

        result = self.api.train_selective([email_content], is_spam=False)
        assert isinstance(result, TrainingResult)
        assert result.messages_processed >= 1

    def test_remove_message(self):
        """Test removing a message."""
        email_content = """From: test@example.com
Subject: Test

This is a test message.
"""

        # Train the message first
        self.api.train_message(email_content, is_spam=False)

        # Remove it
        removed = self.api.remove_message(email_content)
        assert isinstance(removed, bool)

    def test_database_operations(self):
        """Test database export/import operations."""
        # Train some messages
        self.api.train_message(
            "From: test@example.com\nSubject: Test\n\nHello", is_spam=False
        )

        # Export database
        exported = self.api.export_database()
        assert isinstance(exported, list)
        assert len(exported) > 0

        # Check export format
        for item in exported:
            assert len(item) == 3  # (term, good_count, spam_count)
            assert isinstance(item[0], str)
            assert isinstance(item[1], int)
            assert isinstance(item[2], int)

    def test_backup_restore(self):
        """Test database backup and restore."""
        # Train a message
        self.api.train_message(
            "From: test@example.com\nSubject: Test\n\nHello", is_spam=False
        )

        # Create backup
        backup_file = self.db_path / "backup.csv"
        self.api.backup_database(backup_file)
        assert backup_file.exists()

        # Reset database
        self.api.reset_database()

        # Restore from backup
        imported = self.api.restore_database(backup_file)
        assert imported > 0

    def test_cleanup_database(self):
        """Test database cleanup."""
        # Train some messages
        for i in range(3):
            self.api.train_message(
                f"From: test{i}@example.com\nSubject: Test {i}\n\nMessage {i}",
                is_spam=False,
            )

        # Cleanup with aggressive settings
        removed = self.api.cleanup_database(max_count=100, max_age_days=0)
        assert isinstance(removed, int)

    def test_context_manager(self):
        """Test using API as context manager."""
        with MailProbeAPI(self.db_path) as api:
            result = api.classify_text("From: test@example.com\nSubject: Test\n\nHello")
            assert isinstance(result, bool)


class TestBatchMailFilter:
    """Test cases for BatchMailFilter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir)
        self.api = MailProbeAPI(self.db_path)
        self.batch_filter = BatchMailFilter(self.api)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.api.close()
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_classify_batch(self):
        """Test batch classification."""
        messages = [
            "From: test1@example.com\nSubject: Test 1\n\nHello 1",
            "From: test2@example.com\nSubject: Test 2\n\nHello 2",
            "From: test3@example.com\nSubject: Test 3\n\nHello 3",
        ]

        # Test simple batch classification
        results = self.batch_filter.classify_batch(messages)
        assert len(results) == len(messages)
        assert all(isinstance(r, bool) for r in results)

        # Test detailed batch classification
        detailed_results = self.batch_filter.classify_batch(
            messages, return_details=True
        )
        assert len(detailed_results) == len(messages)
        assert all(isinstance(r, ClassificationResult) for r in detailed_results)

    def test_train_batch(self):
        """Test batch training."""
        good_messages = [
            "From: friend1@example.com\nSubject: Meeting\n\nLet's meet tomorrow",
            "From: friend2@example.com\nSubject: Project\n\nHow's the project going?",
        ]

        spam_messages = [
            "From: spammer1@bad.com\nSubject: FREE MONEY\n\nClick here for free money!",
            "From: spammer2@bad.com\nSubject: URGENT\n\nYou've won a prize!",
        ]

        results = self.batch_filter.train_batch(good_messages, spam_messages)

        assert "good" in results
        assert "spam" in results
        assert isinstance(results["good"], TrainingResult)
        assert isinstance(results["spam"], TrainingResult)
        assert results["good"].messages_processed >= 2
        assert results["spam"].messages_processed >= 2


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_classify_email_function(self):
        """Test classify_email convenience function."""
        email_content = "From: test@example.com\nSubject: Test\n\nHello world"

        result = classify_email(email_content, self.db_path)
        assert isinstance(result, bool)

    def test_get_spam_probability_function(self):
        """Test get_spam_probability convenience function."""
        email_content = "From: test@example.com\nSubject: Test\n\nHello world"

        prob = get_spam_probability(email_content, self.db_path)
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

    def test_train_from_directories_function(self):
        """Test train_from_directories convenience function."""
        # Create test directories with email files
        good_dir = self.db_path / "good"
        spam_dir = self.db_path / "spam"
        good_dir.mkdir()
        spam_dir.mkdir()

        # Create test email files
        (good_dir / "email1.txt").write_text(
            "From: friend@example.com\nSubject: Meeting\n\nLet's meet"
        )
        (good_dir / "email2.txt").write_text(
            "From: colleague@example.com\nSubject: Project\n\nProject update"
        )

        (spam_dir / "spam1.txt").write_text(
            "From: spammer@bad.com\nSubject: FREE MONEY\n\nClick here!"
        )
        (spam_dir / "spam2.txt").write_text(
            "From: scammer@evil.com\nSubject: URGENT\n\nYou won!"
        )

        results = train_from_directories(good_dir, spam_dir, self.db_path)

        assert "good" in results
        assert "spam" in results
        assert isinstance(results["good"], TrainingResult)
        assert isinstance(results["spam"], TrainingResult)


class TestClassificationResult:
    """Test cases for ClassificationResult."""

    def test_classification_result_str(self):
        """Test ClassificationResult string representation."""
        result = ClassificationResult(
            is_spam=True,
            probability=0.95,
            confidence=0.9,
            terms_used=15,
            digest="abc123",
            top_terms=[("free", 0.9, 2), ("money", 0.85, 1)],
        )

        str_repr = str(result)
        assert "SPAM" in str_repr
        assert "0.95" in str_repr
        assert "0.9" in str_repr


class TestTrainingResult:
    """Test cases for TrainingResult."""

    def test_training_result_str(self):
        """Test TrainingResult string representation."""
        result = TrainingResult(
            messages_processed=10, messages_updated=5, database_updated=True
        )

        str_repr = str(result)
        assert "processed=10" in str_repr
        assert "updated=5" in str_repr
