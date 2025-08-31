# MailProbe-Py Usage Guide

This guide shows how to use MailProbe-Py for email classifiering with practical examples.

## Installation with Poetry

```bash
# Clone the repository
git clone https://github.com/yourusername/mailprobe-py
cd mailprobe-py

# Install with Poetry
poetry install

# Activate the virtual environment
poetry shell

# Or run commands with poetry run
poetry run mailprobe-py --help
```

## Quick Start

### 1. Create a Database

```bash
poetry run mailprobe-py create-db
```

This creates a database in `~/.mailprobe-py/` by default.

### 2. Train the Filter

Train on good (non-spam) emails:

```bash
poetry run mailprobe-py good ~/mail/inbox
poetry run mailprobe-py good ~/mail/sent
```

Train on spam emails:

```bash
poetry run mailprobe-py spam ~/mail/spam
```

### 3. Score New Emails

Score a single email:

```bash
poetry run mailprobe-py score < new_email.txt
```

Score with detailed term information:

```bash
poetry run mailprobe-py score -T < new_email.txt
```

### 4. Use in Receive Mode

For integration with mail systems (always trains):

```bash
poetry run mailprobe-py receive < incoming_email.txt
```

## Advanced Usage

### Configuration

Create a configuration file:

```bash
poetry run mailprobe-py create-config
```

This creates `~/.mailprobe-py/config.json` with default settings.

### Custom Database Location

```bash
poetry run mailprobe-py -d /path/to/database create-db
poetry run mailprobe-py -d /path/to/database good ~/mail/inbox
```

### Scoring Options

Adjust spam threshold:

```bash
poetry run mailprobe-py -l 0.8 score < email.txt  # Lower threshold (more sensitive)
```

Use aggressive scoring:

```bash
poetry run mailprobe-py -X score < email.txt
```

Apply Paul Graham's original algorithm:

```bash
poetry run mailprobe-py -o graham score < email.txt
```

### Database Management

View database information:

```bash
poetry run mailprobe-py info
```

Clean up old/rare words:

```bash
poetry run mailprobe-py cleanup --max-count 2 --max-age-days 30
```

Export database:

```bash
poetry run mailprobe-py dump --format csv > backup.csv
```

Import database:

```bash
poetry run mailprobe-py import-db backup.csv
```

## Integration Examples

### Procmail Integration

Add to your `.procmailrc`:

```
# Score all incoming mail
:0 fw
| poetry run mailprobe-py receive

# File spam messages
:0:
* ^X-MailProbe: SPAM
spam/
```

### Python API Usage

```python
from pathlib import Path
from mailprobe import MailFilter, FilterConfig
from mailprobe.message import EmailMessage

# Initialize filter
config = FilterConfig()
db_path = Path.home() / ".mailprobe-py"
spam_filter = MailFilter(db_path, config)

# Train on a message
message = EmailMessage("""From: friend@example.com
Subject: Meeting

Let's meet for lunch tomorrow.
""")

spam_filter.train_message(message, is_spam=False)

# Score a message
test_message = EmailMessage("""From: unknown@example.com
Subject: Test

This is a test message.
""")

score = spam_filter.score_message(test_message)
print(f"Spam probability: {score.probability:.3f}")
print(f"Is spam: {score.is_spam}")

spam_filter.close()
```

### Batch Processing

Process multiple mailboxes:

```bash
# Train on multiple good mailboxes
for mailbox in ~/mail/inbox ~/mail/sent ~/mail/work; do
    poetry run mailprobe-py good "$mailbox"
done

# Train on spam
poetry run mailprobe-py spam ~/mail/spam

# Score all messages in a directory
for email in ~/mail/unsorted/*; do
    result=$(poetry run mailprobe-py score "$email")
    echo "$email: $result"
done
```

## Performance Tips

1. **Use appropriate cache size** for your system:
   ```bash
   poetry run mailprobe-py -s 5000 score < email.txt
   ```

2. **Regular cleanup** to maintain performance:
   ```bash
   # Add to crontab for daily cleanup
   0 2 * * * poetry run mailprobe-py cleanup
   ```

3. **Use train mode** instead of receive for better performance:
   ```bash
   poetry run mailprobe-py train < email.txt  # Only updates if needed
   ```

## Troubleshooting

### Database Issues

If you encounter database corruption:

```bash
# Export data
poetry run mailprobe-py dump > backup.csv

# Remove old database
rm -rf ~/.mailprobe-py

# Create new database and import
poetry run mailprobe-py create-db
poetry run mailprobe-py import-db backup.csv
```

### Poor Accuracy

If the filter isn't working well:

1. **Ensure sufficient training data** (at least 100 messages of each type)
2. **Check for imbalanced training** (similar numbers of spam/good messages)
3. **Use selective training** to focus on difficult messages:
   ```bash
   poetry run mailprobe-py train < difficult_email.txt
   ```

### Memory Usage

For large databases, adjust cache size:

```bash
# Smaller cache for memory-constrained systems
poetry run mailprobe-py -s 1000 score < email.txt

# Larger cache for better performance
poetry run mailprobe-py -s 10000 score < email.txt
```

## Configuration Options

### Tokenizer Settings

- `--max-phrase-terms`: Maximum words per phrase (default: 2)
- `--min-term-length`: Minimum word length (default: 3)
- `--no-remove-html`: Keep HTML tags in analysis

### Scoring Settings

- `--spam-threshold`: Spam probability threshold (default: 0.9)
- `--min-word-count`: Minimum count for word probability (default: 5)
- `--terms-for-score`: Number of terms used for scoring (default: 15)

### Special Options

- `-o graham`: Use Paul Graham's original algorithm
- `-o conservative`: Reduce false positives
- `-o aggressive`: Catch more spam (more false positives)

## Best Practices

1. **Start with balanced training data** (similar amounts of spam and good email)
2. **Train regularly** on misclassified messages
3. **Use train mode** for ongoing operation (more efficient than receive mode)
4. **Monitor database size** and clean up periodically
5. **Backup your database** regularly using the export function
6. **Test thoroughly** before deploying in production
