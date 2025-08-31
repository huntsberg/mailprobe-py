#!/usr/bin/env python3
"""Basic test of MailProbe-Py functionality."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, "src")

from mailprobe.filter import MailFilter, FilterConfig
from mailprobe.message import EmailMessage


def main():
    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir)

    print(f"Creating database in {db_path}")

    # Initialize filter
    config = FilterConfig()
    spam_filter = MailFilter(db_path, config)

    # Test with a good message
    good_message = EmailMessage(
        """From: friend@example.com
Subject: Lunch meeting

Let's meet for lunch tomorrow at noon. Looking forward to seeing you!
"""
    )

    print("Training on good message...")
    spam_filter.train_message(good_message, is_spam=False)

    # Test with a spam message
    spam_message = EmailMessage(
        """From: spammer@badsite.com
Subject: FREE MONEY NOW!!!

Click here to get FREE MONEY! Limited time offer!
Buy now! Act fast! Don't miss out!
"""
    )

    print("Training on spam message...")
    spam_filter.train_message(spam_message, is_spam=True)

    # Test scoring
    print("\nScoring messages:")

    test_good = EmailMessage(
        """Subject: Project meeting

Let's discuss the project timeline."""
    )

    test_spam = EmailMessage(
        """Subject: URGENT!!!

FREE money! Click now! Limited offer!"""
    )

    good_score = spam_filter.score_message(test_good)
    spam_score = spam_filter.score_message(test_spam)

    print(
        f"Good message score: {good_score.probability:.3f} (spam: {good_score.is_spam})"
    )
    print(
        f"Spam message score: {spam_score.probability:.3f} (spam: {spam_score.is_spam})"
    )

    # Get database info
    info = spam_filter.get_database_info()
    print(f"\nDatabase info:")
    print(f'  Words: {info["word_count"]}')
    print(f'  Good messages: {info["good_message_count"]}')
    print(f'  Spam messages: {info["spam_message_count"]}')

    spam_filter.close()
    print("\nTest completed successfully!")

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
