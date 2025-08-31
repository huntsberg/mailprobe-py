"""
Configuration management for MailProbe-Py.

This module handles configuration loading, validation, and management
for the email classifier system.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict, fields

from .filter import FilterConfig


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    
    path: str = "~/.mailprobe-py"
    cache_size: int = 2500
    auto_cleanup: bool = True
    cleanup_interval_days: int = 7
    cleanup_max_count: int = 2
    cleanup_max_age_days: int = 14


@dataclass
class TokenizerConfig:
    """Tokenizer configuration settings."""
    
    max_phrase_terms: int = 2
    min_phrase_terms: int = 1
    min_term_length: int = 3
    max_term_length: int = 40
    remove_html: bool = True
    ignore_body: bool = False
    replace_non_ascii: str = 'z'
    
    # Header processing
    process_headers: bool = True
    header_mode: str = "normal"  # normal, all, nox, none
    custom_headers: list = None
    
    def __post_init__(self):
        if self.custom_headers is None:
            self.custom_headers = []


@dataclass
class ScoringConfig:
    """Scoring algorithm configuration settings."""
    
    spam_threshold: float = 0.9
    min_word_count: int = 5
    new_word_score: float = 0.4
    terms_for_score: int = 15
    max_word_repeats: int = 2
    extend_top_terms: bool = False
    min_distance_for_score: float = 0.1
    
    # Scoring modes
    scoring_mode: str = "normal"  # normal, original, alt1


@dataclass
class MailProbeConfig:
    """Main configuration class for MailProbe-Py."""
    
    database: DatabaseConfig = None
    tokenizer: TokenizerConfig = None
    scoring: ScoringConfig = None
    
    # Global settings
    verbose: bool = False
    debug: bool = False
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.tokenizer is None:
            self.tokenizer = TokenizerConfig()
        if self.scoring is None:
            self.scoring = ScoringConfig()
    
    def to_filter_config(self) -> FilterConfig:
        """Convert to FilterConfig for use with MailFilter."""
        return FilterConfig(
            # Scoring parameters
            spam_threshold=self.scoring.spam_threshold,
            min_word_count=self.scoring.min_word_count,
            new_word_score=self.scoring.new_word_score,
            terms_for_score=self.scoring.terms_for_score,
            max_word_repeats=self.scoring.max_word_repeats,
            extend_top_terms=self.scoring.extend_top_terms,
            min_distance_for_score=self.scoring.min_distance_for_score,
            
            # Tokenizer parameters
            max_phrase_terms=self.tokenizer.max_phrase_terms,
            min_phrase_terms=self.tokenizer.min_phrase_terms,
            min_term_length=self.tokenizer.min_term_length,
            max_term_length=self.tokenizer.max_term_length,
            remove_html=self.tokenizer.remove_html,
            ignore_body=self.tokenizer.ignore_body,
            replace_non_ascii=self.tokenizer.replace_non_ascii,
            
            # Database parameters
            cache_size=self.database.cache_size,
        )
    
    def get_database_path(self) -> Path:
        """Get the resolved database path."""
        path = Path(self.database.path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


class ConfigManager:
    """
    Manages configuration loading, saving, and validation.
    
    Supports loading configuration from:
    - JSON files
    - Environment variables
    - Command line arguments
    - Default values
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file
        self._config: Optional[MailProbeConfig] = None
    
    def load_config(self, config_file: Optional[Path] = None) -> MailProbeConfig:
        """
        Load configuration from file or create default.
        
        Args:
            config_file: Optional path to configuration file
            
        Returns:
            MailProbeConfig object
        """
        if config_file:
            self.config_file = config_file
        
        if self.config_file and self.config_file.exists():
            self._config = self._load_from_file(self.config_file)
        else:
            self._config = MailProbeConfig()
        
        return self._config
    
    def save_config(self, config: MailProbeConfig, 
                   config_file: Optional[Path] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            config_file: Optional path to save to (uses default if None)
        """
        if config_file:
            self.config_file = config_file
        
        if not self.config_file:
            raise ValueError("No configuration file specified")
        
        # Ensure directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary and save as JSON
        config_dict = self._config_to_dict(config)
        
        with open(self.config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def get_config(self) -> MailProbeConfig:
        """Get current configuration (loads default if not loaded)."""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def update_from_args(self, args: Dict[str, Any]) -> None:
        """
        Update configuration from command line arguments.
        
        Args:
            args: Dictionary of command line arguments
        """
        if self._config is None:
            self._config = MailProbeConfig()
        
        # Map command line args to config fields
        arg_mappings = {
            # Global settings
            'verbose': ('verbose',),
            'debug': ('debug',),
            
            # Database settings
            'database_path': ('database', 'path'),
            'cache_size': ('database', 'cache_size'),
            
            # Tokenizer settings
            'max_phrase_terms': ('tokenizer', 'max_phrase_terms'),
            'min_phrase_terms': ('tokenizer', 'min_phrase_terms'),
            'min_term_length': ('tokenizer', 'min_term_length'),
            'max_term_length': ('tokenizer', 'max_term_length'),
            'remove_html': ('tokenizer', 'remove_html'),
            'ignore_body': ('tokenizer', 'ignore_body'),
            'replace_non_ascii': ('tokenizer', 'replace_non_ascii'),
            'header_mode': ('tokenizer', 'header_mode'),
            
            # Scoring settings
            'spam_threshold': ('scoring', 'spam_threshold'),
            'min_word_count': ('scoring', 'min_word_count'),
            'new_word_score': ('scoring', 'new_word_score'),
            'terms_for_score': ('scoring', 'terms_for_score'),
            'max_word_repeats': ('scoring', 'max_word_repeats'),
            'extend_top_terms': ('scoring', 'extend_top_terms'),
            'min_distance_for_score': ('scoring', 'min_distance_for_score'),
            'scoring_mode': ('scoring', 'scoring_mode'),
        }
        
        for arg_name, value in args.items():
            if value is not None and arg_name in arg_mappings:
                self._set_nested_value(self._config, arg_mappings[arg_name], value)
    
    def apply_preset(self, preset_name: str) -> None:
        """
        Apply a configuration preset.
        
        Args:
            preset_name: Name of the preset to apply
        """
        if self._config is None:
            self._config = MailProbeConfig()
        
        presets = {
            'graham': self._apply_graham_preset,
            'conservative': self._apply_conservative_preset,
            'aggressive': self._apply_aggressive_preset,
            'fast': self._apply_fast_preset,
        }
        
        if preset_name in presets:
            presets[preset_name]()
        else:
            raise ValueError(f"Unknown preset: {preset_name}")
    
    def _load_from_file(self, config_file: Path) -> MailProbeConfig:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                config_dict = json.load(f)
            
            return self._dict_to_config(config_dict)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"Invalid configuration file {config_file}: {e}")
    
    def _config_to_dict(self, config: MailProbeConfig) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'database': asdict(config.database),
            'tokenizer': asdict(config.tokenizer),
            'scoring': asdict(config.scoring),
            'verbose': config.verbose,
            'debug': config.debug,
        }
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> MailProbeConfig:
        """Convert dictionary to configuration."""
        config = MailProbeConfig()
        
        # Update database config
        if 'database' in config_dict:
            db_dict = config_dict['database']
            config.database = DatabaseConfig(**db_dict)
        
        # Update tokenizer config
        if 'tokenizer' in config_dict:
            tok_dict = config_dict['tokenizer']
            config.tokenizer = TokenizerConfig(**tok_dict)
        
        # Update scoring config
        if 'scoring' in config_dict:
            score_dict = config_dict['scoring']
            config.scoring = ScoringConfig(**score_dict)
        
        # Update global settings
        config.verbose = config_dict.get('verbose', False)
        config.debug = config_dict.get('debug', False)
        
        return config
    
    def _set_nested_value(self, obj: Any, path: tuple, value: Any) -> None:
        """Set a nested value in an object."""
        current = obj
        for key in path[:-1]:
            current = getattr(current, key)
        setattr(current, path[-1], value)
    
    def _apply_graham_preset(self) -> None:
        """Apply Paul Graham's original algorithm settings."""
        self._config.tokenizer.max_phrase_terms = 1
        self._config.tokenizer.remove_html = False
        self._config.tokenizer.min_term_length = 1
        self._config.tokenizer.max_term_length = 90
        self._config.tokenizer.header_mode = "all"
        
        self._config.scoring.terms_for_score = 15
        self._config.scoring.max_word_repeats = 1
        self._config.scoring.new_word_score = 0.4
        self._config.scoring.extend_top_terms = False
        self._config.scoring.scoring_mode = "original"
    
    def _apply_conservative_preset(self) -> None:
        """Apply conservative settings (fewer false positives)."""
        self._config.scoring.spam_threshold = 0.95
        self._config.scoring.min_word_count = 10
        self._config.scoring.new_word_score = 0.3
        self._config.scoring.min_distance_for_score = 0.2
    
    def _apply_aggressive_preset(self) -> None:
        """Apply aggressive settings (catch more spam)."""
        self._config.scoring.spam_threshold = 0.8
        self._config.scoring.min_word_count = 3
        self._config.scoring.new_word_score = 0.6
        self._config.scoring.extend_top_terms = True
    
    def _apply_fast_preset(self) -> None:
        """Apply settings optimized for speed."""
        self._config.tokenizer.max_phrase_terms = 1
        self._config.tokenizer.ignore_body = False
        self._config.scoring.terms_for_score = 10
        self._config.database.cache_size = 5000


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".mailprobe-py" / "config.json"


def load_config(config_file: Optional[Path] = None) -> MailProbeConfig:
    """
    Load configuration from file or create default.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        MailProbeConfig object
    """
    if config_file is None:
        config_file = get_default_config_path()
    
    manager = ConfigManager(config_file)
    return manager.load_config()


def save_config(config: MailProbeConfig, 
               config_file: Optional[Path] = None) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save
        config_file: Optional path to save to
    """
    if config_file is None:
        config_file = get_default_config_path()
    
    manager = ConfigManager(config_file)
    manager.save_config(config)
