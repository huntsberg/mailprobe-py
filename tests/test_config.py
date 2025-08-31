"""Tests for configuration management."""

import pytest
import tempfile
import json
from pathlib import Path

from mailprobe.config import (
    DatabaseConfig, 
    TokenizerConfig, 
    ScoringConfig, 
    MailProbeConfig,
    ConfigManager,
    load_config,
    save_config
)
from mailprobe.filter import FilterConfig


class TestConfigClasses:
    """Test cases for configuration classes."""
    
    def test_database_config(self):
        """Test DatabaseConfig creation and defaults."""
        config = DatabaseConfig()
        
        assert config.path == "~/.mailprobe-py"
        assert config.cache_size == 2500
        assert config.auto_cleanup is True
        assert config.cleanup_interval_days == 7
        assert config.cleanup_max_count == 2
        assert config.cleanup_max_age_days == 14
    
    def test_tokenizer_config(self):
        """Test TokenizerConfig creation and defaults."""
        config = TokenizerConfig()
        
        assert config.max_phrase_terms == 2
        assert config.min_phrase_terms == 1
        assert config.min_term_length == 3
        assert config.max_term_length == 40
        assert config.remove_html is True
        assert config.ignore_body is False
        assert config.replace_non_ascii == 'z'
        assert config.process_headers is True
        assert config.header_mode == "normal"
        assert config.custom_headers == []
    
    def test_scoring_config(self):
        """Test ScoringConfig creation and defaults."""
        config = ScoringConfig()
        
        assert config.spam_threshold == 0.9
        assert config.min_word_count == 5
        assert config.new_word_score == 0.4
        assert config.terms_for_score == 15
        assert config.max_word_repeats == 2
        assert config.extend_top_terms is False
        assert config.min_distance_for_score == 0.1
        assert config.scoring_mode == "normal"
    
    def test_spamprobe_config(self):
        """Test MailProbeConfig creation and composition."""
        config = MailProbeConfig()
        
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.tokenizer, TokenizerConfig)
        assert isinstance(config.scoring, ScoringConfig)
        assert config.verbose is False
        assert config.debug is False
    
    def test_config_to_filter_config(self):
        """Test conversion to FilterConfig."""
        config = MailProbeConfig()
        config.scoring.spam_threshold = 0.8
        config.tokenizer.max_phrase_terms = 3
        config.database.cache_size = 5000
        
        filter_config = config.to_filter_config()
        
        assert isinstance(filter_config, FilterConfig)
        assert filter_config.spam_threshold == 0.8
        assert filter_config.max_phrase_terms == 3
        assert filter_config.cache_size == 5000
    
    def test_get_database_path(self):
        """Test database path resolution."""
        config = MailProbeConfig()
        config.database.path = "~/test_spamprobe"
        
        path = config.get_database_path()
        
        assert isinstance(path, Path)
        assert path.is_absolute()
        assert path.exists()  # Should be created


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_manager_creation(self):
        """Test ConfigManager creation."""
        manager = ConfigManager(self.config_file)
        assert manager.config_file == self.config_file
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        manager = ConfigManager()
        config = manager.load_config()
        
        assert isinstance(config, MailProbeConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.tokenizer, TokenizerConfig)
        assert isinstance(config.scoring, ScoringConfig)
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        # Create custom config
        config = MailProbeConfig()
        config.database.cache_size = 5000
        config.tokenizer.max_phrase_terms = 3
        config.scoring.spam_threshold = 0.8
        config.verbose = True
        
        # Save config
        manager = ConfigManager(self.config_file)
        manager.save_config(config)
        
        assert self.config_file.exists()
        
        # Load config
        loaded_config = manager.load_config()
        
        assert loaded_config.database.cache_size == 5000
        assert loaded_config.tokenizer.max_phrase_terms == 3
        assert loaded_config.scoring.spam_threshold == 0.8
        assert loaded_config.verbose is True
    
    def test_update_from_args(self):
        """Test updating config from command line arguments."""
        manager = ConfigManager()
        config = manager.load_config()
        
        # Update from args
        args = {
            'verbose': True,
            'spam_threshold': 0.8,
            'cache_size': 5000,
            'max_phrase_terms': 3,
            'remove_html': False
        }
        
        manager.update_from_args(args)
        updated_config = manager.get_config()
        
        assert updated_config.verbose is True
        assert updated_config.scoring.spam_threshold == 0.8
        assert updated_config.database.cache_size == 5000
        assert updated_config.tokenizer.max_phrase_terms == 3
        assert updated_config.tokenizer.remove_html is False
    
    def test_apply_presets(self):
        """Test applying configuration presets."""
        manager = ConfigManager()
        config = manager.load_config()
        
        # Test Graham preset
        manager.apply_preset('graham')
        graham_config = manager.get_config()
        
        assert graham_config.tokenizer.max_phrase_terms == 1
        assert graham_config.tokenizer.remove_html is False
        assert graham_config.scoring.terms_for_score == 15
        assert graham_config.scoring.max_word_repeats == 1
        
        # Test conservative preset
        manager = ConfigManager()
        manager.load_config()
        manager.apply_preset('conservative')
        conservative_config = manager.get_config()
        
        assert conservative_config.scoring.spam_threshold == 0.95
        assert conservative_config.scoring.min_word_count == 10
        
        # Test aggressive preset
        manager = ConfigManager()
        manager.load_config()
        manager.apply_preset('aggressive')
        aggressive_config = manager.get_config()
        
        assert aggressive_config.scoring.spam_threshold == 0.8
        assert aggressive_config.scoring.min_word_count == 3
        assert aggressive_config.scoring.extend_top_terms is True
    
    def test_invalid_preset(self):
        """Test applying invalid preset."""
        manager = ConfigManager()
        manager.load_config()
        
        with pytest.raises(ValueError, match="Unknown preset"):
            manager.apply_preset('invalid_preset')
    
    def test_invalid_config_file(self):
        """Test loading invalid configuration file."""
        # Create invalid JSON file
        invalid_file = Path(self.temp_dir) / "invalid.json"
        invalid_file.write_text("{ invalid json }")
        
        manager = ConfigManager(invalid_file)
        
        with pytest.raises(ValueError, match="Invalid configuration file"):
            manager.load_config()


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_config_function(self):
        """Test load_config convenience function."""
        config = load_config(self.config_file)
        
        assert isinstance(config, MailProbeConfig)
    
    def test_save_config_function(self):
        """Test save_config convenience function."""
        config = MailProbeConfig()
        config.verbose = True
        
        save_config(config, self.config_file)
        
        assert self.config_file.exists()
        
        # Verify saved content
        with open(self.config_file) as f:
            data = json.load(f)
        
        assert data['verbose'] is True
    
    def test_config_file_structure(self):
        """Test the structure of saved configuration files."""
        config = MailProbeConfig()
        save_config(config, self.config_file)
        
        with open(self.config_file) as f:
            data = json.load(f)
        
        # Check required sections
        assert 'database' in data
        assert 'tokenizer' in data
        assert 'scoring' in data
        assert 'verbose' in data
        assert 'debug' in data
        
        # Check database section
        db_config = data['database']
        assert 'path' in db_config
        assert 'cache_size' in db_config
        
        # Check tokenizer section
        tok_config = data['tokenizer']
        assert 'max_phrase_terms' in tok_config
        assert 'remove_html' in tok_config
        
        # Check scoring section
        score_config = data['scoring']
        assert 'spam_threshold' in score_config
        assert 'min_word_count' in score_config
