#!/usr/bin/env python3
"""
Example script showing how to integrate MailProbe-Py into other applications.

This demonstrates the object-oriented API and various usage patterns.
"""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mailprobe import (
    MailProbeAPI,
    BatchMailFilter,
    classify_email,
    get_spam_probability,
    train_from_directories
)


def basic_usage_example():
    """Demonstrate basic API usage."""
    print("=== Basic Usage Example ===")
    
    # Create email classifier instance
    spam_filter = MailProbeAPI()
    
    # Example email content
    good_email = """From: colleague@company.com
Subject: Meeting tomorrow
Date: Mon, 1 Jan 2024 10:00:00 +0000

Hi there,

Don't forget about our meeting tomorrow at 2 PM.
We'll be discussing the quarterly reports.

Best regards,
John
"""
    
    spam_email = """From: noreply@suspicious-site.com
Subject: !!!URGENT!!! FREE MONEY WAITING FOR YOU!!!
Date: Mon, 1 Jan 2024 10:00:00 +0000

CONGRATULATIONS!!! You have WON $1,000,000!!!

Click here NOW to claim your prize:
http://definitely-not-a-scam.com/claim-now

This offer expires in 24 HOURS! Don't miss out!
ACT NOW! CLICK HERE! FREE MONEY!
"""
    
    # Train the filter
    print("Training on good email...")
    spam_filter.train_message(good_email, is_spam=False)
    
    print("Training on spam email...")
    spam_filter.train_message(spam_email, is_spam=True)
    
    # Test classification
    test_email = """From: unknown@example.com
Subject: Quick question
Date: Mon, 1 Jan 2024 11:00:00 +0000

Hi,

I have a quick question about the project.
Could we schedule a brief call this week?

Thanks,
Alice
"""
    
    # Simple classification
    is_spam = spam_filter.classify_text(test_email)
    print(f"Test email is spam: {is_spam}")
    
    # Detailed classification
    result = spam_filter.classify_text(test_email, return_details=True)
    print(f"Detailed result: {result}")
    print(f"Probability: {result.probability:.3f}")
    print(f"Confidence: {result.confidence:.3f}")
    
    # Get database statistics
    stats = spam_filter.get_database_stats()
    print(f"Database stats: {stats}")
    
    spam_filter.close()


def batch_processing_example():
    """Demonstrate batch processing capabilities."""
    print("\n=== Batch Processing Example ===")
    
    # Create API instance
    api = MailProbeAPI()
    batch_filter = BatchMailFilter(api)
    
    # Sample emails for batch processing
    emails = [
        "From: friend@example.com\nSubject: Lunch\n\nWant to grab lunch?",
        "From: spammer@bad.com\nSubject: FREE PILLS\n\nBuy cheap pills now!",
        "From: boss@company.com\nSubject: Report\n\nPlease send the monthly report.",
        "From: scammer@evil.com\nSubject: WINNER\n\nYou've won a million dollars!",
    ]
    
    # Batch classification
    results = batch_filter.classify_batch(emails, return_details=True)
    
    print("Batch classification results:")
    for i, result in enumerate(results):
        print(f"Email {i+1}: {result}")
    
    # Batch training
    good_emails = [emails[0], emails[2]]  # Lunch and report emails
    spam_emails = [emails[1], emails[3]]  # Pills and winner emails
    
    training_results = batch_filter.train_batch(good_emails, spam_emails)
    print(f"Training results: {training_results}")
    
    api.close()


def convenience_functions_example():
    """Demonstrate convenience functions."""
    print("\n=== Convenience Functions Example ===")
    
    email_content = """From: marketing@store.com
Subject: 50% Off Sale!
Date: Mon, 1 Jan 2024 12:00:00 +0000

Don't miss our biggest sale of the year!
50% off everything in store.
Valid until end of month.
"""
    
    # Quick classification
    is_spam = classify_email(email_content)
    print(f"Email is spam: {is_spam}")
    
    # Get probability
    probability = get_spam_probability(email_content)
    print(f"Spam probability: {probability:.3f}")


def advanced_integration_example():
    """Demonstrate advanced integration patterns."""
    print("\n=== Advanced Integration Example ===")
    
    class MyEmailProcessor:
        """Example email processor class integrating MailProbe."""
        
        def __init__(self, database_path=None):
            self.spam_filter = MailProbeAPI(database_path)
            self.processed_count = 0
            self.spam_count = 0
        
        def process_email(self, email_content, sender_whitelist=None):
            """Process an email with email classifiering and whitelisting."""
            self.processed_count += 1
            
            # Check sender whitelist first
            if sender_whitelist and self._is_whitelisted(email_content, sender_whitelist):
                return {"action": "deliver", "reason": "whitelisted", "spam_probability": 0.0}
            
            # Classify with email classifier
            result = self.spam_filter.classify_text(email_content, return_details=True)
            
            if result.is_spam:
                self.spam_count += 1
                action = "quarantine" if result.confidence > 0.8 else "flag"
            else:
                action = "deliver"
            
            return {
                "action": action,
                "spam_probability": result.probability,
                "confidence": result.confidence,
                "terms_used": result.terms_used
            }
        
        def train_from_user_feedback(self, email_content, user_marked_as_spam):
            """Train based on user feedback."""
            return self.spam_filter.train_message(email_content, user_marked_as_spam, force_update=True)
        
        def get_statistics(self):
            """Get processing statistics."""
            db_stats = self.spam_filter.get_database_stats()
            return {
                "emails_processed": self.processed_count,
                "spam_detected": self.spam_count,
                "spam_rate": self.spam_count / max(self.processed_count, 1),
                "database_words": db_stats["word_count"],
                "trained_messages": db_stats["total_message_count"]
            }
        
        def _is_whitelisted(self, email_content, whitelist):
            """Check if sender is whitelisted."""
            # Simple whitelist check (in practice, you'd parse headers properly)
            for domain in whitelist:
                if f"@{domain}" in email_content:
                    return True
            return False
        
        def close(self):
            """Clean up resources."""
            self.spam_filter.close()
    
    # Use the custom email processor
    processor = MyEmailProcessor()
    
    # Define whitelist
    whitelist = ["company.com", "trusted-partner.org"]
    
    # Process some emails
    emails_to_process = [
        "From: boss@company.com\nSubject: Meeting\n\nTeam meeting at 3 PM.",
        "From: spammer@bad.com\nSubject: URGENT\n\nClick here for free money!",
        "From: partner@trusted-partner.org\nSubject: Contract\n\nContract details attached.",
    ]
    
    print("Processing emails with custom processor:")
    for i, email in enumerate(emails_to_process):
        result = processor.process_email(email, whitelist)
        print(f"Email {i+1}: {result}")
    
    # Show statistics
    stats = processor.get_statistics()
    print(f"Processing statistics: {stats}")
    
    processor.close()


def context_manager_example():
    """Demonstrate context manager usage."""
    print("\n=== Context Manager Example ===")
    
    # Using context manager ensures proper cleanup
    with MailProbeAPI() as spam_filter:
        # Train some data
        spam_filter.train_good(["From: friend@example.com\nSubject: Hi\n\nHow are you?"])
        spam_filter.train_spam(["From: spammer@bad.com\nSubject: FREE\n\nFree money!"])
        
        # Classify
        test_email = "From: test@example.com\nSubject: Question\n\nI have a question."
        result = spam_filter.classify_text(test_email, return_details=True)
        print(f"Classification result: {result}")
    
    # Filter is automatically closed when exiting the context


def backup_restore_example():
    """Demonstrate database backup and restore."""
    print("\n=== Backup and Restore Example ===")
    
    with MailProbeAPI() as spam_filter:
        # Train some data
        spam_filter.train_good(["From: friend@example.com\nSubject: Meeting\n\nLet's meet tomorrow."])
        spam_filter.train_spam(["From: spammer@bad.com\nSubject: FREE MONEY\n\nClick here!"])
        
        print("Original database stats:")
        print(spam_filter.get_database_stats())
        
        # Create backup
        backup_path = Path("spam_filter_backup.csv")
        spam_filter.backup_database(backup_path)
        print(f"Backup created: {backup_path}")
        
        # Reset database
        spam_filter.reset_database()
        print("Database reset")
        
        # Restore from backup
        imported = spam_filter.restore_database(backup_path)
        print(f"Restored {imported} words from backup")
        
        print("Restored database stats:")
        print(spam_filter.get_database_stats())
        
        # Clean up
        backup_path.unlink()


def main():
    """Run all examples."""
    print("MailProbe-Py Integration Examples")
    print("=" * 40)
    
    try:
        basic_usage_example()
        batch_processing_example()
        convenience_functions_example()
        advanced_integration_example()
        context_manager_example()
        backup_restore_example()
        
        print("\n" + "=" * 40)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
