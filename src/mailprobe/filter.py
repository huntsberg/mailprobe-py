"""
Main email classifier implementation using Bayesian analysis.

This module provides the core MailFilter class that combines tokenization,
database operations, and Bayesian scoring to classify email messages.
"""

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass

from .database import WordDatabase, WordData
from .tokenizer import EmailTokenizer, Token
from .message import EmailMessage


@dataclass
class FilterConfig:
    """Configuration settings for the email classifier."""
    
    # Scoring parameters
    spam_threshold: float = 0.9
    min_word_count: int = 5
    new_word_score: float = 0.4
    terms_for_score: int = 15
    max_word_repeats: int = 2
    extend_top_terms: bool = False
    min_distance_for_score: float = 0.1
    
    # Tokenizer parameters
    max_phrase_terms: int = 2
    min_phrase_terms: int = 1
    min_term_length: int = 3
    max_term_length: int = 40
    remove_html: bool = True
    ignore_body: bool = False
    replace_non_ascii: str = 'z'
    
    # Database parameters
    cache_size: int = 2500


class MailScore(NamedTuple):
    """Represents the result of scoring a message."""
    probability: float
    is_spam: bool
    confidence: float
    terms_used: int
    top_terms: List[Tuple[str, float, int]]  # (term, probability, count)


class MailFilter:
    """
    Main email classifier class implementing Bayesian spam detection.
    
    This class provides the primary interface for email classifiering operations:
    - Training on spam and good messages
    - Scoring new messages
    - Managing the word frequency database
    - Handling message classification and reclassification
    """
    
    def __init__(self, database_path: Path, config: Optional[FilterConfig] = None):
        """
        Initialize the email classifier.
        
        Args:
            database_path: Path to the database directory
            config: Filter configuration (uses defaults if None)
        """
        self.config = config or FilterConfig()
        self.database_path = Path(database_path)
        
        # Initialize database
        db_file = self.database_path / "words.db"
        self.database = WordDatabase(db_file, self.config.cache_size)
        
        # Initialize tokenizer
        self.tokenizer = EmailTokenizer(
            max_phrase_terms=self.config.max_phrase_terms,
            min_phrase_terms=self.config.min_phrase_terms,
            min_term_length=self.config.min_term_length,
            max_term_length=self.config.max_term_length,
            remove_html=self.config.remove_html,
            ignore_body=self.config.ignore_body,
            replace_non_ascii=self.config.replace_non_ascii
        )
    
    def score_message(self, message: EmailMessage) -> MailScore:
        """
        Score a message and return spam probability.
        
        Args:
            message: EmailMessage to score
            
        Returns:
            MailScore with probability and analysis details
        """
        # Tokenize the message
        tokens = self.tokenizer.tokenize_message(message)
        
        # Get word data from database and calculate probabilities
        scored_tokens = []
        good_count, spam_count = self.database.get_message_counts()
        
        for token in tokens:
            word_data = self.database.get_word_data(token.get_key())
            if word_data:
                probability = word_data.calculate_probability(
                    good_count, spam_count,
                    self.config.min_word_count,
                    self.config.new_word_score
                )
            else:
                probability = self.config.new_word_score
            
            token.probability = probability
            scored_tokens.append(token)
        
        # Select most significant tokens for scoring
        significant_tokens = self._select_significant_tokens(scored_tokens)
        
        # Calculate final probability using Bayesian combination
        final_probability = self._calculate_bayesian_probability(significant_tokens)
        
        # Determine if message is spam
        is_spam = final_probability >= self.config.spam_threshold
        
        # Calculate confidence (distance from neutral 0.5)
        confidence = abs(final_probability - 0.5) * 2
        
        # Get top terms for analysis
        top_terms = [(token.get_key(), token.probability, token.count) 
                     for token in significant_tokens[:10]]
        
        return MailScore(
            probability=final_probability,
            is_spam=is_spam,
            confidence=confidence,
            terms_used=len(significant_tokens),
            top_terms=top_terms
        )
    
    def train_message(self, message: EmailMessage, is_spam: bool, 
                     force_update: bool = False) -> bool:
        """
        Train the filter on a message.
        
        Args:
            message: EmailMessage to train on
            is_spam: Whether the message is spam
            force_update: Force update even if message was seen before
            
        Returns:
            True if database was updated, False otherwise
        """
        # Check if we've seen this message before
        exists, previous_classification = self.database.contains_message(message.digest)
        
        if exists and not force_update:
            if previous_classification == is_spam:
                # Same classification, no update needed
                return False
            else:
                # Reclassification needed
                return self._reclassify_message(message, is_spam, previous_classification)
        
        # New message or forced update
        return self._add_message_to_database(message, is_spam)
    
    def train_message_selective(self, message: EmailMessage, is_spam: bool) -> bool:
        """
        Train on a message only if it's difficult to classify correctly.
        
        This implements the "train" mode from original MailProbe that only
        updates the database for messages that need it.
        
        Args:
            message: EmailMessage to potentially train on
            is_spam: Whether the message is spam
            
        Returns:
            True if database was updated, False otherwise
        """
        # Check if we've seen this message before
        exists, previous_classification = self.database.contains_message(message.digest)
        
        if exists:
            if previous_classification != is_spam:
                # Reclassification needed
                return self._reclassify_message(message, is_spam, previous_classification)
            else:
                # Already correctly classified
                return False
        
        # For new messages, only train if the score is not confident
        score = self.score_message(message)
        
        # Check if classification matches expected result
        if score.is_spam != is_spam:
            # Misclassified, definitely need to train
            return self._add_message_to_database(message, is_spam)
        
        # Check confidence level
        if score.confidence < 0.8:  # Not very confident
            return self._add_message_to_database(message, is_spam)
        
        # Message is correctly and confidently classified, no training needed
        return False
    
    def remove_message(self, message: EmailMessage) -> bool:
        """
        Remove a message from the database.
        
        Args:
            message: EmailMessage to remove
            
        Returns:
            True if message was found and removed, False otherwise
        """
        exists, was_spam = self.database.contains_message(message.digest)
        
        if not exists:
            return False
        
        # Tokenize message to get terms to decrement
        tokens = self.tokenizer.tokenize_message(message)
        
        # Count token frequencies
        token_counts = {}
        for token in tokens:
            key = token.get_key()
            token_counts[key] = token_counts.get(key, 0) + 1
        
        # Prepare updates (negative counts to decrement)
        updates = {}
        for term, count in token_counts.items():
            if was_spam:
                updates[term] = (0, -count)  # Decrement spam count
            else:
                updates[term] = (-count, 0)  # Decrement good count
        
        # Apply updates
        self.database.update_word_counts(updates)
        self.database.remove_message(message.digest)
        
        return True
    
    def cleanup_database(self, max_count: int = 2, max_age_days: int = 7) -> int:
        """
        Clean up old/rare words from the database.
        
        Args:
            max_count: Maximum total count for words to be removed
            max_age_days: Maximum age in days for words to be removed
            
        Returns:
            Number of words removed
        """
        return self.database.cleanup_old_words(max_count, max_age_days)
    
    def purge_database(self, max_count: int = 2) -> int:
        """
        Purge words with low counts regardless of age.
        
        Args:
            max_count: Maximum total count for words to be removed
            
        Returns:
            Number of words removed
        """
        return self.database.purge_words(max_count)
    
    def get_database_info(self) -> Dict[str, any]:
        """Get information about the database."""
        return self.database.get_database_info()
    
    def export_database(self) -> List[Tuple[str, int, int]]:
        """Export all words from the database."""
        return list(self.database.export_words())
    
    def import_database(self, word_data: List[Tuple[str, int, int]]) -> int:
        """Import words into the database."""
        return self.database.import_words(iter(word_data))
    
    def _select_significant_tokens(self, tokens: List[Token]) -> List[Token]:
        """
        Select the most significant tokens for scoring.
        
        This implements the token selection algorithm from original MailProbe.
        """
        # Count token frequencies
        token_freq = {}
        for token in tokens:
            key = token.get_key()
            if key not in token_freq:
                token_freq[key] = token
                token_freq[key].count = 1
            else:
                token_freq[key].count += 1
        
        # Convert to list and filter by significance
        unique_tokens = list(token_freq.values())
        
        # Filter tokens by distance from neutral (0.5)
        significant_tokens = []
        for token in unique_tokens:
            distance = abs(token.probability - 0.5)
            if distance >= self.config.min_distance_for_score:
                significant_tokens.append(token)
        
        # Sort by significance (distance from 0.5, then by frequency)
        significant_tokens.sort(
            key=lambda t: (abs(t.probability - 0.5), t.count),
            reverse=True
        )
        
        # Select top tokens
        selected_tokens = []
        term_counts = {}
        
        for token in significant_tokens:
            # Limit repeats of same term
            current_count = term_counts.get(token.get_key(), 0)
            if current_count < self.config.max_word_repeats:
                selected_tokens.append(token)
                term_counts[token.get_key()] = current_count + 1
                
                # Stop when we have enough terms
                if len(selected_tokens) >= self.config.terms_for_score:
                    break
        
        # Extend with additional significant terms if configured
        if (self.config.extend_top_terms and 
            len(selected_tokens) < len(significant_tokens)):
            
            for token in significant_tokens[len(selected_tokens):]:
                if (token.probability <= 0.1 or token.probability >= 0.9):
                    selected_tokens.append(token)
                    if len(selected_tokens) >= self.config.terms_for_score * 2:
                        break
        
        return selected_tokens
    
    def _calculate_bayesian_probability(self, tokens: List[Token]) -> float:
        """
        Calculate final spam probability using Bayesian combination.
        
        This implements the probability combination algorithm from Paul Graham's
        "A Plan for Spam" with improvements from MailProbe.
        """
        if not tokens:
            return self.config.new_word_score
        
        # Calculate product of probabilities and inverse probabilities
        spam_product = 1.0
        good_product = 1.0
        
        for token in tokens:
            # Use token frequency as weight
            weight = min(token.count, 5)  # Cap weight to avoid dominance
            
            for _ in range(weight):
                spam_product *= token.probability
                good_product *= (1.0 - token.probability)
                
                # Prevent underflow
                if spam_product < 1e-200:
                    spam_product = 1e-200
                if good_product < 1e-200:
                    good_product = 1e-200
        
        # Combine using Bayesian formula
        try:
            probability = spam_product / (spam_product + good_product)
        except (ZeroDivisionError, OverflowError):
            probability = self.config.new_word_score
        
        # Ensure reasonable bounds
        return max(0.0001, min(0.9999, probability))
    
    def _add_message_to_database(self, message: EmailMessage, is_spam: bool) -> bool:
        """Add a new message to the database."""
        # Tokenize message
        tokens = self.tokenizer.tokenize_message(message)
        
        # Count token frequencies
        token_counts = {}
        for token in tokens:
            key = token.get_key()
            token_counts[key] = token_counts.get(key, 0) + 1
        
        # Prepare updates
        updates = {}
        for term, count in token_counts.items():
            if is_spam:
                updates[term] = (0, count)  # Increment spam count
            else:
                updates[term] = (count, 0)  # Increment good count
        
        # Apply updates
        self.database.update_word_counts(updates)
        self.database.add_message(message.digest, is_spam)
        
        return True
    
    def _reclassify_message(self, message: EmailMessage, new_classification: bool,
                           old_classification: bool) -> bool:
        """Reclassify a message by updating word counts."""
        # Tokenize message
        tokens = self.tokenizer.tokenize_message(message)
        
        # Count token frequencies
        token_counts = {}
        for token in tokens:
            key = token.get_key()
            token_counts[key] = token_counts.get(key, 0) + 1
        
        # Prepare updates (remove old classification, add new)
        updates = {}
        for term, count in token_counts.items():
            good_delta = 0
            spam_delta = 0
            
            # Remove old classification
            if old_classification:  # Was spam
                spam_delta -= count
            else:  # Was good
                good_delta -= count
            
            # Add new classification
            if new_classification:  # Now spam
                spam_delta += count
            else:  # Now good
                good_delta += count
            
            updates[term] = (good_delta, spam_delta)
        
        # Apply updates
        self.database.update_word_counts(updates)
        self.database.add_message(message.digest, new_classification)
        
        return True
    
    def close(self) -> None:
        """Close the filter and database."""
        self.database.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
