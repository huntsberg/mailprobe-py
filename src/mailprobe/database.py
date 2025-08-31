"""
Word frequency database for email classifiering.

This module provides database functionality for storing and retrieving
word frequencies used in Bayesian spam analysis.
"""

import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator
from contextlib import contextmanager

from .tokenizer import Token


class WordData:
    """Represents word frequency data for a single term."""
    
    def __init__(self, term: str, good_count: int = 0, spam_count: int = 0, 
                 last_update: Optional[int] = None):
        self.term = term
        self.good_count = good_count
        self.spam_count = spam_count
        self.last_update = last_update or int(time.time())
    
    @property
    def total_count(self) -> int:
        """Get total count (good + spam)."""
        return self.good_count + self.spam_count
    
    def calculate_probability(self, good_message_count: int, spam_message_count: int,
                            min_word_count: int = 5, new_word_score: float = 0.4) -> float:
        """
        Calculate spam probability for this word using Bayesian analysis.
        
        Args:
            good_message_count: Total number of good messages in database
            spam_message_count: Total number of spam messages in database
            min_word_count: Minimum count required for calculated probability
            new_word_score: Default probability for new/rare words
            
        Returns:
            Probability that a message containing this word is spam (0.0 to 1.0)
        """
        # Use weighted count (good count doubled) as in original MailProbe
        weighted_count = (self.good_count * 2) + self.spam_count
        
        if weighted_count < min_word_count:
            return new_word_score
        
        # Calculate probability using Bayesian formula
        if good_message_count == 0 and spam_message_count == 0:
            return new_word_score
        
        # Probability of word appearing in spam vs good messages
        spam_prob = self.spam_count / max(spam_message_count, 1)
        good_prob = self.good_count / max(good_message_count, 1)
        
        # Bayesian probability
        if spam_prob + good_prob == 0:
            return new_word_score
        
        probability = spam_prob / (spam_prob + good_prob)
        
        # Clamp to reasonable bounds
        return max(0.01, min(0.99, probability))
    
    def update_counts(self, good_delta: int, spam_delta: int) -> None:
        """Update word counts and timestamp."""
        self.good_count = max(0, self.good_count + good_delta)
        self.spam_count = max(0, self.spam_count + spam_delta)
        self.last_update = int(time.time())
    
    def __str__(self) -> str:
        return f"WordData({self.term}, good={self.good_count}, spam={self.spam_count})"
    
    def __repr__(self) -> str:
        return self.__str__()


class WordDatabase:
    """
    SQLite-based database for storing word frequency data.
    
    This class provides thread-safe access to word frequency data used
    in Bayesian email classifiering. It supports:
    - Atomic updates to word counts
    - Message digest tracking for duplicate detection
    - Database cleanup and maintenance
    - Export/import functionality
    """
    
    def __init__(self, db_path: Path, cache_size: int = 2500):
        """
        Initialize the word database.
        
        Args:
            db_path: Path to the SQLite database file
            cache_size: Size of in-memory word cache
        """
        self.db_path = Path(db_path)
        self.cache_size = cache_size
        self._cache: Dict[str, WordData] = {}
        self._cache_lock = threading.RLock()
        self._db_lock = threading.RLock()
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database tables if they don't exist."""
        with self._get_connection() as conn:
            # Word frequency table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS words (
                    term TEXT PRIMARY KEY,
                    good_count INTEGER DEFAULT 0,
                    spam_count INTEGER DEFAULT 0,
                    last_update INTEGER DEFAULT 0
                )
            ''')
            
            # Message digest table for duplicate detection
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    digest TEXT PRIMARY KEY,
                    is_spam INTEGER,
                    timestamp INTEGER DEFAULT 0
                )
            ''')
            
            # Database metadata
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_words_counts ON words(good_count, spam_count)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_words_update ON words(last_update)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_spam ON messages(is_spam)')
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper locking."""
        with self._db_lock:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=10000')
            try:
                yield conn
            finally:
                conn.close()
    
    def get_word_data(self, term: str) -> Optional[WordData]:
        """
        Get word frequency data for a term.
        
        Args:
            term: The word/phrase to look up
            
        Returns:
            WordData object or None if not found
        """
        # Check cache first
        with self._cache_lock:
            if term in self._cache:
                return self._cache[term]
        
        # Query database
        with self._get_connection() as conn:
            cursor = conn.execute(
                'SELECT good_count, spam_count, last_update FROM words WHERE term = ?',
                (term,)
            )
            row = cursor.fetchone()
            
            if row:
                word_data = WordData(term, row[0], row[1], row[2])
                
                # Add to cache
                with self._cache_lock:
                    if len(self._cache) >= self.cache_size:
                        # Remove oldest entry (simple LRU)
                        oldest_term = next(iter(self._cache))
                        del self._cache[oldest_term]
                    self._cache[term] = word_data
                
                return word_data
        
        return None
    
    def update_word_counts(self, updates: Dict[str, Tuple[int, int]]) -> None:
        """
        Update word counts for multiple terms atomically.
        
        Args:
            updates: Dictionary mapping terms to (good_delta, spam_delta) tuples
        """
        if not updates:
            return
        
        current_time = int(time.time())
        
        with self._get_connection() as conn:
            # Update cache first
            with self._cache_lock:
                for term, (good_delta, spam_delta) in updates.items():
                    if term in self._cache:
                        self._cache[term].update_counts(good_delta, spam_delta)
            
            # Batch update database
            for term, (good_delta, spam_delta) in updates.items():
                conn.execute('''
                    INSERT INTO words (term, good_count, spam_count, last_update)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(term) DO UPDATE SET
                        good_count = max(0, good_count + ?),
                        spam_count = max(0, spam_count + ?),
                        last_update = ?
                ''', (term, max(0, good_delta), max(0, spam_delta), current_time,
                      good_delta, spam_delta, current_time))
            
            conn.commit()
    
    def add_message(self, digest: str, is_spam: bool) -> None:
        """
        Add a message digest to track processed messages.
        
        Args:
            digest: Message digest (MD5 hash)
            is_spam: Whether the message is spam
        """
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO messages (digest, is_spam, timestamp)
                VALUES (?, ?, ?)
            ''', (digest, int(is_spam), int(time.time())))
            conn.commit()
    
    def contains_message(self, digest: str) -> Tuple[bool, Optional[bool]]:
        """
        Check if a message has been processed before.
        
        Args:
            digest: Message digest to check
            
        Returns:
            Tuple of (exists, is_spam_if_exists)
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                'SELECT is_spam FROM messages WHERE digest = ?',
                (digest,)
            )
            row = cursor.fetchone()
            
            if row:
                return True, bool(row[0])
            return False, None
    
    def remove_message(self, digest: str) -> None:
        """Remove a message digest from the database."""
        with self._get_connection() as conn:
            conn.execute('DELETE FROM messages WHERE digest = ?', (digest,))
            conn.commit()
    
    def get_message_counts(self) -> Tuple[int, int]:
        """
        Get total message counts.
        
        Returns:
            Tuple of (good_message_count, spam_message_count)
        """
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    SUM(CASE WHEN is_spam = 0 THEN 1 ELSE 0 END) as good_count,
                    SUM(CASE WHEN is_spam = 1 THEN 1 ELSE 0 END) as spam_count
                FROM messages
            ''')
            row = cursor.fetchone()
            return (row[0] or 0, row[1] or 0)
    
    def get_word_count(self) -> int:
        """Get total number of unique words in database."""
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM words')
            return cursor.fetchone()[0]
    
    def cleanup_old_words(self, max_count: int = 2, max_age_days: int = 7) -> int:
        """
        Remove old words with low counts from the database.
        
        Args:
            max_count: Maximum total count for words to be removed
            max_age_days: Maximum age in days for words to be removed
            
        Returns:
            Number of words removed
        """
        cutoff_time = int(time.time()) - (max_age_days * 24 * 60 * 60)
        
        with self._get_connection() as conn:
            cursor = conn.execute('''
                DELETE FROM words 
                WHERE (good_count + spam_count) <= ? 
                AND last_update < ?
            ''', (max_count, cutoff_time))
            
            removed_count = cursor.rowcount
            conn.commit()
            
            # Clear cache to ensure consistency
            with self._cache_lock:
                self._cache.clear()
            
            return removed_count
    
    def purge_words(self, max_count: int = 2) -> int:
        """
        Remove all words with count below threshold regardless of age.
        
        Args:
            max_count: Maximum total count for words to be removed
            
        Returns:
            Number of words removed
        """
        with self._get_connection() as conn:
            cursor = conn.execute('''
                DELETE FROM words 
                WHERE (good_count + spam_count) < ?
            ''', (max_count,))
            
            removed_count = cursor.rowcount
            conn.commit()
            
            # Clear cache to ensure consistency
            with self._cache_lock:
                self._cache.clear()
            
            return removed_count
    
    def export_words(self) -> Iterator[Tuple[str, int, int]]:
        """
        Export all words from the database.
        
        Yields:
            Tuples of (term, good_count, spam_count)
        """
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT term, good_count, spam_count FROM words ORDER BY term')
            for row in cursor:
                yield (row[0], row[1], row[2])
    
    def import_words(self, word_data: Iterator[Tuple[str, int, int]]) -> int:
        """
        Import words into the database.
        
        Args:
            word_data: Iterator of (term, good_count, spam_count) tuples
            
        Returns:
            Number of words imported
        """
        count = 0
        current_time = int(time.time())
        
        with self._get_connection() as conn:
            for term, good_count, spam_count in word_data:
                conn.execute('''
                    INSERT OR REPLACE INTO words (term, good_count, spam_count, last_update)
                    VALUES (?, ?, ?, ?)
                ''', (term, good_count, spam_count, current_time))
                count += 1
                
                # Commit in batches for better performance
                if count % 1000 == 0:
                    conn.commit()
            
            conn.commit()
        
        # Clear cache to ensure consistency
        with self._cache_lock:
            self._cache.clear()
        
        return count
    
    def vacuum(self) -> None:
        """Vacuum the database to reclaim space and optimize performance."""
        with self._get_connection() as conn:
            conn.execute('VACUUM')
    
    def get_database_info(self) -> Dict[str, any]:
        """Get information about the database."""
        with self._get_connection() as conn:
            # Get word count
            cursor = conn.execute('SELECT COUNT(*) FROM words')
            word_count = cursor.fetchone()[0]
            
            # Get message counts
            good_count, spam_count = self.get_message_counts()
            
            # Get database file size
            file_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            return {
                'word_count': word_count,
                'good_message_count': good_count,
                'spam_message_count': spam_count,
                'total_message_count': good_count + spam_count,
                'database_file_size': file_size,
                'cache_size': len(self._cache),
                'database_path': str(self.db_path)
            }
    
    def close(self) -> None:
        """Close the database and clear cache."""
        with self._cache_lock:
            self._cache.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
