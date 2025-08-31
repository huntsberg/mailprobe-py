"""Tests for multi-category classification."""

import pytest
import tempfile
import json
from pathlib import Path

from mailprobe.multi_category import (
    MultiCategoryFilter,
    FolderBasedClassifier,
    CategoryResult,
    CategoryTrainingResult,
    classify_into_categories,
    train_from_folder_structure,
)
from mailprobe.message import EmailMessage


class TestMultiCategoryFilter:
    """Test cases for MultiCategoryFilter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir)
        self.categories = ["work", "personal", "newsletters", "spam"]
        self.classifier = MultiCategoryFilter(self.categories, self.db_path)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.classifier.close()
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_classifier_initialization(self):
        """Test classifier initialization."""
        assert self.classifier.categories == self.categories
        assert self.classifier.database_path == self.db_path
        assert len(self.classifier.filters) == len(self.categories)

        # Each category should have its own filter
        for category in self.categories:
            assert category in self.classifier.filters

    def test_train_category(self):
        """Test training on a specific category."""
        emails = [
            "From: boss@company.com\nSubject: Meeting\n\nTeam meeting tomorrow.",
            "From: colleague@work.com\nSubject: Project\n\nProject update needed.",
        ]

        result = self.classifier.train_category("work", emails)

        assert isinstance(result, CategoryTrainingResult)
        assert result.category == "work"
        assert result.messages_processed == 2
        assert result.database_updated

    def test_train_invalid_category(self):
        """Test training with invalid category."""
        with pytest.raises(ValueError, match="Unknown category"):
            self.classifier.train_category("invalid", ["test email"])

    def test_classify_basic(self):
        """Test basic classification."""
        # Train some categories
        work_emails = ["From: boss@company.com\nSubject: Meeting\n\nTeam meeting."]
        personal_emails = ["From: friend@gmail.com\nSubject: Lunch\n\nWant lunch?"]

        self.classifier.train_category("work", work_emails)
        self.classifier.train_category("personal", personal_emails)

        # Test classification
        test_email = "From: colleague@work.com\nSubject: Project\n\nProject discussion."
        result = self.classifier.classify(test_email)

        assert isinstance(result, CategoryResult)
        assert result.category in self.categories
        assert 0.0 <= result.probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_with_all_scores(self):
        """Test classification with all scores returned."""
        # Train categories
        for category in self.categories:
            emails = [
                f"From: test@{category}.com\nSubject: {category}\n\nTest {category} email."
            ]
            self.classifier.train_category(category, emails)

        test_email = "From: test@example.com\nSubject: Test\n\nTest email."
        result = self.classifier.classify(test_email, return_all_scores=True)

        assert isinstance(result.all_scores, dict)
        assert len(result.all_scores) == len(self.categories)

        for category in self.categories:
            assert category in result.all_scores
            assert 0.0 <= result.all_scores[category] <= 1.0

    def test_get_category_stats(self):
        """Test getting statistics for a category."""
        # Train a category
        emails = ["From: test@work.com\nSubject: Test\n\nTest email."]
        self.classifier.train_category("work", emails)

        stats = self.classifier.get_category_stats("work")

        assert isinstance(stats, dict)
        assert "word_count" in stats
        assert "total_message_count" in stats
        assert stats["word_count"] > 0

    def test_get_category_stats_invalid(self):
        """Test getting stats for invalid category."""
        with pytest.raises(ValueError, match="Unknown category"):
            self.classifier.get_category_stats("invalid")

    def test_get_all_stats(self):
        """Test getting statistics for all categories."""
        # Train some categories
        for category in ["work", "personal"]:
            emails = [f"From: test@{category}.com\nSubject: Test\n\nTest email."]
            self.classifier.train_category(category, emails)

        all_stats = self.classifier.get_all_stats()

        assert isinstance(all_stats, dict)
        assert len(all_stats) == len(self.categories)

        for category in self.categories:
            assert category in all_stats
            assert isinstance(all_stats[category], dict)

    def test_cleanup_category(self):
        """Test cleaning up a specific category."""
        # Train a category
        emails = ["From: test@work.com\nSubject: Test\n\nTest email."]
        self.classifier.train_category("work", emails)

        removed = self.classifier.cleanup_category("work", max_count=1, max_age_days=0)

        assert isinstance(removed, int)
        assert removed >= 0

    def test_cleanup_all_categories(self):
        """Test cleaning up all categories."""
        # Train some categories
        for category in ["work", "personal"]:
            emails = [f"From: test@{category}.com\nSubject: Test\n\nTest email."]
            self.classifier.train_category(category, emails)

        results = self.classifier.cleanup_all_categories(max_count=1, max_age_days=0)

        assert isinstance(results, dict)
        assert len(results) == len(self.categories)

        for category in self.categories:
            assert category in results
            assert isinstance(results[category], int)

    def test_export_import_category(self):
        """Test exporting and importing category data."""
        # Train a category
        emails = ["From: test@work.com\nSubject: Test\n\nTest work email."]
        self.classifier.train_category("work", emails)

        # Export data
        exported = self.classifier.export_category("work")

        assert isinstance(exported, list)
        assert len(exported) > 0

        # Check export format
        for item in exported:
            assert len(item) == 3  # (term, good_count, spam_count)
            assert isinstance(item[0], str)
            assert isinstance(item[1], int)
            assert isinstance(item[2], int)

        # Import data (to same category for testing)
        imported = self.classifier.import_category("work", exported)

        assert isinstance(imported, int)
        assert imported > 0

    def test_save_load_configuration(self):
        """Test saving and loading configuration."""
        config_file = Path(self.temp_dir) / "config.json"

        # Save configuration
        self.classifier.save_configuration(config_file)

        assert config_file.exists()

        # Check configuration content
        with open(config_file) as f:
            config_data = json.load(f)

        assert "categories" in config_data
        assert "database_path" in config_data
        assert "filter_config" in config_data
        assert config_data["categories"] == self.categories

        # Load configuration
        loaded_classifier = MultiCategoryFilter.load_configuration(config_file)

        assert loaded_classifier.categories == self.categories
        assert isinstance(loaded_classifier.config, type(self.classifier.config))

        loaded_classifier.close()

    def test_context_manager(self):
        """Test using classifier as context manager."""
        categories = ["test1", "test2"]

        with MultiCategoryFilter(categories, self.db_path) as classifier:
            assert classifier.categories == categories

            # Train and classify
            emails = ["From: test@example.com\nSubject: Test\n\nTest email."]
            result = classifier.train_category("test1", emails)
            assert isinstance(result, CategoryTrainingResult)


class TestFolderBasedClassifier:
    """Test cases for FolderBasedClassifier."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir) / "emails"
        self.base_path.mkdir()

        # Create test folder structure
        self.categories = ["work", "personal", "spam"]
        self.test_emails = {
            "work": [
                "From: boss@company.com\nSubject: Meeting\n\nTeam meeting tomorrow.",
                "From: client@business.com\nSubject: Project\n\nProject update needed.",
            ],
            "personal": [
                "From: friend@gmail.com\nSubject: Lunch\n\nWant to have lunch?",
                "From: family@home.com\nSubject: Visit\n\nComing to visit soon.",
            ],
            "spam": [
                "From: scam@bad.com\nSubject: FREE MONEY\n\nClick for free money!",
                "From: phish@evil.com\nSubject: URGENT\n\nAccount needs attention!",
            ],
        }

        # Create folders and email files
        for category, emails in self.test_emails.items():
            category_path = self.base_path / category
            category_path.mkdir()

            for i, email_content in enumerate(emails):
                email_file = category_path / f"email_{i+1}.txt"
                email_file.write_text(email_content)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_folder_discovery(self):
        """Test automatic folder discovery."""
        classifier = FolderBasedClassifier(self.base_path)

        try:
            discovered = classifier.get_categories()
            assert set(discovered) == set(self.categories)
        finally:
            classifier.close()

    def test_train_from_folders(self):
        """Test training from folder structure."""
        with FolderBasedClassifier(self.base_path) as classifier:
            results = classifier.train_from_folders()

            assert isinstance(results, dict)
            assert len(results) == len(self.categories)

            for category in self.categories:
                assert category in results
                assert isinstance(results[category], CategoryTrainingResult)
                assert results[category].messages_processed > 0

    def test_classify_email(self):
        """Test classifying an email."""
        with FolderBasedClassifier(self.base_path) as classifier:
            # Train from folders
            classifier.train_from_folders()

            # Test classification
            test_email = (
                "From: colleague@work.com\nSubject: Report\n\nPlease review the report."
            )
            result = classifier.classify(test_email)

            assert isinstance(result, CategoryResult)
            assert result.category in self.categories

    def test_get_folder_path(self):
        """Test getting folder path for category."""
        with FolderBasedClassifier(self.base_path) as classifier:
            for category in self.categories:
                folder_path = classifier.get_folder_path(category)
                assert folder_path == self.base_path / category
                assert folder_path.exists()

    def test_move_email_to_folder(self):
        """Test moving email to category folder."""
        # Create test email file
        test_email_path = Path(self.temp_dir) / "test_email.txt"
        test_email_path.write_text(
            "From: test@example.com\nSubject: Test\n\nTest email."
        )

        with FolderBasedClassifier(self.base_path) as classifier:
            # Move email to work folder
            new_path = classifier.move_email_to_folder(test_email_path, "work")

            # Check that file was moved
            assert not test_email_path.exists()
            assert new_path.exists()
            assert new_path.parent == classifier.get_folder_path("work")

    def test_classify_and_move(self):
        """Test classifying and moving email."""
        # Create test email file
        test_email_path = Path(self.temp_dir) / "test_email.txt"
        test_email_path.write_text(
            "From: boss@company.com\nSubject: Urgent\n\nUrgent work matter."
        )

        with FolderBasedClassifier(self.base_path) as classifier:
            # Train from folders
            classifier.train_from_folders()

            # Classify and move with low confidence threshold
            result, moved_path = classifier.classify_and_move(
                test_email_path, confidence_threshold=0.0
            )

            assert isinstance(result, CategoryResult)
            if moved_path:  # If confidence was high enough
                assert moved_path.exists()
                assert not test_email_path.exists()

    def test_nonexistent_base_path(self):
        """Test with nonexistent base path."""
        nonexistent_path = Path(self.temp_dir) / "nonexistent"

        with pytest.raises(ValueError, match="Base path does not exist"):
            FolderBasedClassifier(nonexistent_path)

    def test_empty_base_path(self):
        """Test with empty base path."""
        empty_path = Path(self.temp_dir) / "empty"
        empty_path.mkdir()

        with pytest.raises(ValueError, match="No valid category folders found"):
            FolderBasedClassifier(empty_path)


class TestCategoryResult:
    """Test cases for CategoryResult."""

    def test_category_result_creation(self):
        """Test CategoryResult creation."""
        result = CategoryResult(
            category="work",
            probability=0.8,
            confidence=0.6,
            all_scores={"work": 0.8, "personal": 0.2},
        )

        assert result.category == "work"
        assert result.probability == 0.8
        assert result.confidence == 0.6
        assert result.all_scores == {"work": 0.8, "personal": 0.2}

    def test_category_result_str(self):
        """Test CategoryResult string representation."""
        result = CategoryResult(
            category="spam", probability=0.95, confidence=0.9, all_scores={}
        )

        str_repr = str(result)
        assert "spam" in str_repr
        assert "0.95" in str_repr
        assert "0.9" in str_repr


class TestCategoryTrainingResult:
    """Test cases for CategoryTrainingResult."""

    def test_training_result_creation(self):
        """Test CategoryTrainingResult creation."""
        result = CategoryTrainingResult(
            category="work",
            messages_processed=10,
            messages_updated=8,
            database_updated=True,
        )

        assert result.category == "work"
        assert result.messages_processed == 10
        assert result.messages_updated == 8
        assert result.database_updated is True

    def test_training_result_str(self):
        """Test CategoryTrainingResult string representation."""
        result = CategoryTrainingResult(
            category="personal",
            messages_processed=5,
            messages_updated=3,
            database_updated=True,
        )

        str_repr = str(result)
        assert "personal" in str_repr
        assert "processed=5" in str_repr
        assert "updated=3" in str_repr


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_classify_into_categories(self):
        """Test classify_into_categories convenience function."""
        categories = ["test1", "test2"]
        email_content = "From: test@example.com\nSubject: Test\n\nTest email."

        result = classify_into_categories(email_content, categories, self.temp_dir)

        assert isinstance(result, CategoryResult)
        assert result.category in categories

    def test_train_from_folder_structure(self):
        """Test train_from_folder_structure convenience function."""
        # Create test folder structure
        base_path = Path(self.temp_dir) / "emails"
        base_path.mkdir()

        # Create test folders and files
        for category in ["work", "personal"]:
            category_path = base_path / category
            category_path.mkdir()

            email_file = category_path / "test.txt"
            email_file.write_text(
                f"From: test@{category}.com\nSubject: Test\n\nTest {category} email."
            )

        results = train_from_folder_structure(base_path, self.temp_dir)

        assert isinstance(results, dict)
        assert "work" in results
        assert "personal" in results

        for category, result in results.items():
            assert isinstance(result, CategoryTrainingResult)
            assert result.messages_processed > 0
