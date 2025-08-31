# Object-Oriented API Guide

MailProbe-Py provides a clean, object-oriented API that makes it easy to integrate email classifiering into other Python applications and scripts.

## Quick Start

### Basic Usage

```python
from spamprobe import MailProbeAPI

# Create a email classifier instance
spam_filter = MailProbeAPI()

# Train on some messages
spam_filter.train_good(["From: friend@example.com\nSubject: Meeting\n\nLet's meet tomorrow."])
spam_filter.train_spam(["From: spammer@bad.com\nSubject: FREE MONEY\n\nClick here for free money!"])

# Classify new messages
email_content = "From: unknown@example.com\nSubject: Question\n\nI have a question about the project."
is_spam = spam_filter.classify_text(email_content)
print(f"Is spam: {is_spam}")

# Get detailed results
result = spam_filter.classify_text(email_content, return_details=True)
print(f"Probability: {result.probability:.3f}")
print(f"Confidence: {result.confidence:.3f}")

# Clean up
spam_filter.close()
```

### Using Context Manager (Recommended)

```python
from spamprobe import MailProbeAPI

with MailProbeAPI() as spam_filter:
    # Train and classify
    spam_filter.train_good(["From: friend@example.com\nSubject: Hi\n\nHow are you?"])
    is_spam = spam_filter.classify_text("From: test@example.com\nSubject: Test\n\nHello")
    print(f"Is spam: {is_spam}")
# Automatically closed when exiting the context
```

## API Classes

### MailProbeAPI

The main class for email classifiering operations.

#### Constructor

```python
MailProbeAPI(database_path=None, config=None, auto_create=True)
```

- `database_path`: Path to database directory (default: `~/.mailprobe-py`)
- `config`: Configuration object or dictionary
- `auto_create`: Automatically create database if it doesn't exist

#### Classification Methods

```python
# Simple classification (returns bool)
is_spam = spam_filter.classify_text(email_content)
is_spam = spam_filter.classify(email_file_path)

# Detailed classification (returns ClassificationResult)
result = spam_filter.classify_text(email_content, return_details=True)

# Get spam probability only
probability = spam_filter.get_spam_probability(email_content)
```

#### Training Methods

```python
# Train on individual messages
updated = spam_filter.train_message(email_content, is_spam=False)

# Train on multiple messages
result = spam_filter.train_good(["email1", "email2", "email3"])
result = spam_filter.train_spam(["spam1", "spam2", "spam3"])

# Selective training (only on difficult messages)
result = spam_filter.train_selective(["email1", "email2"], is_spam=False)
```

#### Database Management

```python
# Get database statistics
stats = spam_filter.get_database_stats()

# Backup and restore
spam_filter.backup_database("backup.csv")
spam_filter.restore_database("backup.csv")

# Cleanup old words
removed = spam_filter.cleanup_database(max_count=2, max_age_days=7)

# Reset database
spam_filter.reset_database()
```

### BatchMailFilter

For processing large volumes of email efficiently.

```python
from spamprobe import MailProbeAPI, BatchMailFilter

with MailProbeAPI() as api:
    batch_filter = BatchMailFilter(api)
    
    # Classify multiple messages
    emails = ["email1", "email2", "email3"]
    results = batch_filter.classify_batch(emails, return_details=True)
    
    # Train on multiple message sets
    good_emails = ["good1", "good2"]
    spam_emails = ["spam1", "spam2"]
    training_results = batch_filter.train_batch(good_emails, spam_emails)
```

## Result Objects

### ClassificationResult

Returned by detailed classification methods:

```python
result = spam_filter.classify_text(email, return_details=True)

print(f"Is spam: {result.is_spam}")
print(f"Probability: {result.probability}")  # 0.0 to 1.0
print(f"Confidence: {result.confidence}")    # 0.0 to 1.0
print(f"Terms used: {result.terms_used}")
print(f"Message digest: {result.digest}")
print(f"Top terms: {result.top_terms}")      # List of (term, prob, count)
```

### TrainingResult

Returned by training methods:

```python
result = spam_filter.train_good(["email1", "email2"])

print(f"Messages processed: {result.messages_processed}")
print(f"Messages updated: {result.messages_updated}")
print(f"Database updated: {result.database_updated}")
```

## Convenience Functions

For quick one-off operations:

```python
from spamprobe import classify_email, get_spam_probability, train_from_directories

# Quick classification
is_spam = classify_email(email_content)

# Get probability
probability = get_spam_probability(email_content)

# Train from directories
results = train_from_directories("good_emails/", "spam_emails/")
```

## Configuration

### Using Configuration Objects

```python
from spamprobe import MailProbeAPI, FilterConfig

# Custom configuration
config = FilterConfig(
    spam_threshold=0.8,        # Lower threshold (more sensitive)
    min_word_count=10,         # Require more training data
    terms_for_score=20         # Use more terms for scoring
)

spam_filter = MailProbeAPI(config=config)
```

### Using Configuration Dictionary

```python
config = {
    "spam_threshold": 0.8,
    "min_word_count": 10,
    "remove_html": True,
    "max_phrase_terms": 3
}

spam_filter = MailProbeAPI(config=config)
```

## Integration Patterns

### Email Server Integration

```python
class EmailFilter:
    def __init__(self):
        self.spam_filter = MailProbeAPI()
        self.whitelist = ["company.com", "trusted.org"]
    
    def process_email(self, email_content):
        # Check whitelist first
        if self._is_whitelisted(email_content):
            return {"action": "deliver", "reason": "whitelisted"}
        
        # Classify with email classifier
        result = self.spam_filter.classify_text(email_content, return_details=True)
        
        if result.is_spam:
            if result.confidence > 0.9:
                return {"action": "reject", "probability": result.probability}
            else:
                return {"action": "quarantine", "probability": result.probability}
        else:
            return {"action": "deliver", "probability": result.probability}
    
    def learn_from_feedback(self, email_content, is_spam):
        """Learn from user feedback"""
        self.spam_filter.train_message(email_content, is_spam, force_update=True)
```

### Batch Email Processing

```python
import os
from pathlib import Path
from spamprobe import MailProbeAPI, BatchMailFilter

def process_mailbox_directory(mailbox_dir):
    with MailProbeAPI() as api:
        batch_filter = BatchMailFilter(api)
        
        # Get all email files
        email_files = list(Path(mailbox_dir).glob("*.eml"))
        
        # Classify in batches
        batch_size = 100
        for i in range(0, len(email_files), batch_size):
            batch = email_files[i:i + batch_size]
            results = batch_filter.classify_batch(batch, return_details=True)
            
            # Process results
            for email_file, result in zip(batch, results):
                if result.is_spam:
                    # Move to spam folder
                    spam_dir = Path(mailbox_dir) / "spam"
                    spam_dir.mkdir(exist_ok=True)
                    email_file.rename(spam_dir / email_file.name)
```

### Training from User Actions

```python
class AdaptiveMailFilter:
    def __init__(self):
        self.spam_filter = MailProbeAPI()
        self.pending_training = []
    
    def classify_email(self, email_content):
        result = self.spam_filter.classify_text(email_content, return_details=True)
        
        # Store for potential training if confidence is low
        if result.confidence < 0.8:
            self.pending_training.append((email_content, result))
        
        return result
    
    def user_marked_as_spam(self, email_content):
        """User manually marked email as spam"""
        self.spam_filter.train_message(email_content, is_spam=True, force_update=True)
        self._remove_from_pending(email_content)
    
    def user_marked_as_good(self, email_content):
        """User manually marked email as not spam"""
        self.spam_filter.train_message(email_content, is_spam=False, force_update=True)
        self._remove_from_pending(email_content)
    
    def train_pending_low_confidence(self):
        """Train on messages where we had low confidence"""
        for email_content, result in self.pending_training:
            # Train based on our original classification
            self.spam_filter.train_message_selective(email_content, result.is_spam)
        
        self.pending_training.clear()
```

## Error Handling

```python
from spamprobe import MailProbeAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    with MailProbeAPI() as spam_filter:
        # Your email classifiering code here
        result = spam_filter.classify_text(email_content)
        
except FileNotFoundError:
    logger.error("Database not found - run create-db first")
except PermissionError:
    logger.error("Permission denied accessing database")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Performance Tips

1. **Use context managers** to ensure proper cleanup
2. **Batch operations** when processing many emails
3. **Adjust cache size** based on your memory constraints
4. **Regular cleanup** to maintain database performance
5. **Use selective training** to minimize database updates

```python
# Performance-optimized configuration
config = {
    "cache_size": 10000,      # Larger cache for better performance
    "terms_for_score": 10,    # Fewer terms for faster scoring
    "min_word_count": 3       # Lower threshold for faster training
}

spam_filter = MailProbeAPI(config=config)
```

## Thread Safety

The MailProbeAPI is **not thread-safe**. For multi-threaded applications, create separate instances for each thread or use proper locking:

```python
import threading
from spamprobe import MailProbeAPI

# Thread-local storage for email classifiers
thread_local = threading.local()

def get_spam_filter():
    if not hasattr(thread_local, 'spam_filter'):
        thread_local.spam_filter = MailProbeAPI()
    return thread_local.spam_filter

def classify_email_threadsafe(email_content):
    spam_filter = get_spam_filter()
    return spam_filter.classify_text(email_content)
```
