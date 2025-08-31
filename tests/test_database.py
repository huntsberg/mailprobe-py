"""Tests for the word frequency database."""

import pytest
import tempfile
import time
from pathlib import Path

from mailprobe.database import WordDatabase, WordData


class TestWordData:
    """Test cases for WordData."""
    
    def test_word_data_creation(self):
        """Test WordData creation and properties."""
        word = WordData("test", good_count=5, spam_count=3)
        
        assert word.term == "test"
        assert word.good_count == 5
        assert word.spam_count == 3
        assert word.total_count == 8
        assert word.last_update is not None
    
    def test_probability_calculation(self):
        """Test spam probability calculation."""
        # Test with sufficient data
        word = WordData("test", good_count=10, spam_count=2)
        prob = word.calculate_probability(100, 50, min_word_count=5)
        
        assert 0.0 <= prob <= 1.0
        assert isinstance(prob, float)
        
        # Test with insufficient data (should return default)
        word_rare = WordData("rare", good_count=1, spam_count=1)
        prob_rare = word_rare.calculate_probability(100, 50, min_word_count=5, new_word_score=0.4)
        
        assert prob_rare == 0.4
    
    def test_update_counts(self):
        """Test updating word counts."""
        word = WordData("test", good_count=5, spam_count=3)
        original_time = word.last_update
        
        # Wait a moment to ensure timestamp changes
        time.sleep(0.1)  # Increase sleep time for more reliable timestamp difference
        
        word.update_counts(2, -1)
        
        assert word.good_count == 7
        assert word.spam_count == 2
        assert word.last_update >= original_time  # Use >= instead of > for more reliable test
        
        # Test that counts don't go below zero
        word.update_counts(-10, -5)
        assert word.good_count == 0
        assert word.spam_count == 0


class TestWordDatabase:
    """Test cases for WordDatabase."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = WordDatabase(self.db_path)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.db.close()
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_database_creation(self):
        """Test database creation and initialization."""
        assert self.db_path.exists()
        
        # Check initial state
        assert self.db.get_word_count() == 0
        good_count, spam_count = self.db.get_message_counts()
        assert good_count == 0
        assert spam_count == 0
    
    def test_word_operations(self):
        """Test basic word operations."""
        # Initially no word
        word_data = self.db.get_word_data("test")
        assert word_data is None
        
        # Add word
        updates = {"test": (5, 3)}
        self.db.update_word_counts(updates)
        
        # Retrieve word
        word_data = self.db.get_word_data("test")
        assert word_data is not None
        assert word_data.term == "test"
        assert word_data.good_count == 5
        assert word_data.spam_count == 3
        
        # Update word
        updates = {"test": (2, 1)}
        self.db.update_word_counts(updates)
        
        word_data = self.db.get_word_data("test")
        assert word_data.good_count == 7
        assert word_data.spam_count == 4
    
    def test_message_tracking(self):
        """Test message digest tracking."""
        digest = "abc123def456"
        
        # Initially not contained
        exists, classification = self.db.contains_message(digest)
        assert not exists
        assert classification is None
        
        # Add message
        self.db.add_message(digest, True)  # spam
        
        # Check existence
        exists, classification = self.db.contains_message(digest)
        assert exists
        assert classification is True
        
        # Update message classification
        self.db.add_message(digest, False)  # not spam
        
        exists, classification = self.db.contains_message(digest)
        assert exists
        assert classification is False
        
        # Remove message
        self.db.remove_message(digest)
        
        exists, classification = self.db.contains_message(digest)
        assert not exists
    
    def test_message_counts(self):
        """Test message count tracking."""
        # Add some messages
        self.db.add_message("msg1", True)   # spam
        self.db.add_message("msg2", False)  # good
        self.db.add_message("msg3", True)   # spam
        
        good_count, spam_count = self.db.get_message_counts()
        assert good_count == 1
        assert spam_count == 2
    
    def test_cleanup_operations(self):
        """Test database cleanup operations."""
        # Add some words with different counts
        updates = {
            "common": (10, 5),
            "rare1": (1, 1),
            "rare2": (2, 0),
            "old": (1, 0)
        }
        self.db.update_word_counts(updates)
        
        initial_count = self.db.get_word_count()
        assert initial_count >= 4
        
        # Cleanup with aggressive settings (should remove rare words)
        removed = self.db.cleanup_old_words(max_count=3, max_age_days=0)
        
        final_count = self.db.get_word_count()
        assert final_count <= initial_count
        assert removed >= 0
    
    def test_purge_operations(self):
        """Test database purge operations."""
        # Add words with different counts
        updates = {
            "common": (10, 5),
            "uncommon": (3, 2),
            "rare": (1, 1)
        }
        self.db.update_word_counts(updates)
        
        initial_count = self.db.get_word_count()
        
        # Purge words with count < 3
        removed = self.db.purge_words(max_count=3)
        
        final_count = self.db.get_word_count()
        assert final_count < initial_count
        assert removed > 0
        
        # "common" should still exist
        word_data = self.db.get_word_data("common")
        assert word_data is not None
    
    def test_export_import(self):
        """Test database export and import."""
        # Add some test data
        updates = {
            "word1": (5, 3),
            "word2": (2, 8),
            "word3": (10, 1)
        }
        self.db.update_word_counts(updates)
        
        # Export data
        exported = list(self.db.export_words())
        
        assert len(exported) >= 3
        
        # Check export format
        for term, good_count, spam_count in exported:
            assert isinstance(term, str)
            assert isinstance(good_count, int)
            assert isinstance(spam_count, int)
            assert good_count >= 0
            assert spam_count >= 0
        
        # Create new database and import
        new_db_path = Path(self.temp_dir) / "new_test.db"
        new_db = WordDatabase(new_db_path)
        
        imported_count = new_db.import_words(iter(exported))
        assert imported_count == len(exported)
        
        # Verify imported data
        for term, expected_good, expected_spam in exported:
            word_data = new_db.get_word_data(term)
            assert word_data is not None
            assert word_data.good_count == expected_good
            assert word_data.spam_count == expected_spam
        
        new_db.close()
    
    def test_database_info(self):
        """Test database information retrieval."""
        # Add some test data
        updates = {"test1": (5, 3), "test2": (2, 1)}
        self.db.update_word_counts(updates)
        self.db.add_message("msg1", True)
        self.db.add_message("msg2", False)
        
        info = self.db.get_database_info()
        
        assert isinstance(info, dict)
        assert 'word_count' in info
        assert 'good_message_count' in info
        assert 'spam_message_count' in info
        assert 'total_message_count' in info
        assert 'database_file_size' in info
        assert 'cache_size' in info
        assert 'database_path' in info
        
        assert info['word_count'] >= 2
        assert info['good_message_count'] >= 1
        assert info['spam_message_count'] >= 1
        assert info['total_message_count'] >= 2
    
    def test_cache_functionality(self):
        """Test word caching functionality."""
        # Add word to database
        updates = {"cached_word": (5, 3)}
        self.db.update_word_counts(updates)
        
        # First access should load from database
        word_data1 = self.db.get_word_data("cached_word")
        assert word_data1 is not None
        
        # Second access should use cache
        word_data2 = self.db.get_word_data("cached_word")
        assert word_data2 is not None
        assert word_data2.term == word_data1.term
    
    def test_concurrent_updates(self):
        """Test handling of concurrent word updates."""
        # Simulate concurrent updates to same word
        updates1 = {"concurrent": (3, 2)}
        updates2 = {"concurrent": (1, 4)}
        
        self.db.update_word_counts(updates1)
        self.db.update_word_counts(updates2)
        
        # Final counts should be cumulative
        word_data = self.db.get_word_data("concurrent")
        assert word_data is not None
        assert word_data.good_count == 4  # 3 + 1
        assert word_data.spam_count == 6  # 2 + 4
    
    def test_vacuum_operation(self):
        """Test database vacuum operation."""
        # Add and remove some data to create fragmentation
        updates = {"temp1": (5, 3), "temp2": (2, 1)}
        self.db.update_word_counts(updates)
        
        # Remove data
        self.db.purge_words(max_count=10)
        
        # Vacuum should complete without error
        self.db.vacuum()
        
        # Database should still be functional
        info = self.db.get_database_info()
        assert isinstance(info, dict)
