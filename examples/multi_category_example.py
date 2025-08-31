#!/usr/bin/env python3
"""
Multi-category classification example for MailProbe-Py.

This example demonstrates how to use MailProbe-Py for classifying emails
into multiple categories beyond just spam/not-spam, such as different
folders or types of emails.
"""

import sys
from pathlib import Path
import tempfile
import shutil

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mailprobe import (
    MultiCategoryFilter,
    FolderBasedClassifier,
    classify_into_categories,
    train_from_folder_structure
)


def basic_multi_category_example():
    """Demonstrate basic multi-category classification."""
    print("=== Basic Multi-Category Classification ===")
    
    # Define categories
    categories = ['work', 'personal', 'newsletters', 'spam']
    
    # Create multi-category filter
    with MultiCategoryFilter(categories) as classifier:
        
        # Sample emails for different categories
        work_emails = [
            "From: boss@company.com\nSubject: Quarterly Report\n\nPlease prepare the quarterly report by Friday.",
            "From: colleague@company.com\nSubject: Meeting Tomorrow\n\nDon't forget about our team meeting at 2 PM.",
            "From: hr@company.com\nSubject: Benefits Update\n\nNew health insurance options are now available.",
        ]
        
        personal_emails = [
            "From: friend@gmail.com\nSubject: Weekend Plans\n\nWant to grab dinner this weekend?",
            "From: mom@family.com\nSubject: Family Reunion\n\nDon't forget about the family reunion next month.",
            "From: dentist@clinic.com\nSubject: Appointment Reminder\n\nYour dental appointment is tomorrow at 3 PM.",
        ]
        
        newsletter_emails = [
            "From: newsletter@techsite.com\nSubject: Weekly Tech News\n\nHere are this week's top technology stories.",
            "From: updates@shopping.com\nSubject: New Deals Available\n\nCheck out our latest deals and discounts.",
            "From: news@magazine.com\nSubject: Monthly Newsletter\n\nYour monthly magazine newsletter is here.",
        ]
        
        spam_emails = [
            "From: noreply@suspicious.com\nSubject: FREE MONEY NOW!!!\n\nClick here to get FREE MONEY! Limited time offer!",
            "From: scammer@fake.com\nSubject: You've Won!!!\n\nCongratulations! You've won a million dollars!",
            "From: phisher@bad.com\nSubject: Urgent Account Update\n\nYour account will be closed unless you click here NOW!",
        ]
        
        # Train on each category
        print("Training on different categories...")
        
        work_result = classifier.train_category('work', work_emails)
        print(f"Work training: {work_result}")
        
        personal_result = classifier.train_category('personal', personal_emails)
        print(f"Personal training: {personal_result}")
        
        newsletter_result = classifier.train_category('newsletters', newsletter_emails)
        print(f"Newsletter training: {newsletter_result}")
        
        spam_result = classifier.train_category('spam', spam_emails)
        print(f"Spam training: {spam_result}")
        
        # Test classification on new emails
        test_emails = [
            ("From: project@company.com\nSubject: Project Update\n\nThe project is on track for completion.", "work"),
            ("From: sister@family.com\nSubject: Birthday Party\n\nYou're invited to my birthday party!", "personal"),
            ("From: daily@news.com\nSubject: Daily Digest\n\nToday's top news stories.", "newsletters"),
            ("From: winner@scam.com\nSubject: CONGRATULATIONS!!!\n\nYou've won the lottery!", "spam"),
        ]
        
        print("\nClassifying test emails:")
        for email_content, expected in test_emails:
            result = classifier.classify(email_content, return_all_scores=True)
            print(f"Expected: {expected:12} | Classified: {result.category:12} | Confidence: {result.confidence:.3f}")
            print(f"  All scores: {result.all_scores}")
        
        # Show category statistics
        print("\nCategory Statistics:")
        stats = classifier.get_all_stats()
        for category, category_stats in stats.items():
            print(f"{category:12}: {category_stats['word_count']} words, "
                  f"{category_stats['total_message_count']} messages")


def folder_based_classification_example():
    """Demonstrate folder-based classification."""
    print("\n=== Folder-Based Classification ===")
    
    # Create temporary directory structure
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create folder structure
        folders = {
            'work': [
                "From: boss@company.com\nSubject: Meeting\n\nTeam meeting at 3 PM.",
                "From: client@business.com\nSubject: Project\n\nProject deadline is next week.",
            ],
            'personal': [
                "From: friend@gmail.com\nSubject: Lunch\n\nWant to have lunch tomorrow?",
                "From: family@home.com\nSubject: Visit\n\nComing to visit this weekend.",
            ],
            'newsletters': [
                "From: news@site.com\nSubject: Weekly Update\n\nThis week's news digest.",
                "From: deals@store.com\nSubject: Sale\n\nBig sale this weekend only!",
            ],
            'spam': [
                "From: scam@bad.com\nSubject: FREE MONEY\n\nClick here for free money!",
                "From: phish@evil.com\nSubject: URGENT\n\nYour account needs immediate attention!",
            ]
        }
        
        # Create folders and email files
        for folder_name, emails in folders.items():
            folder_path = temp_dir / folder_name
            folder_path.mkdir()
            
            for i, email_content in enumerate(emails):
                email_file = folder_path / f"email_{i+1}.txt"
                email_file.write_text(email_content)
        
        print(f"Created test folder structure in: {temp_dir}")
        
        # Create folder-based classifier
        with FolderBasedClassifier(temp_dir) as classifier:
            print(f"Discovered categories: {classifier.get_categories()}")
            
            # Train from folders
            training_results = classifier.train_from_folders()
            print("\nTraining results:")
            for category, result in training_results.items():
                print(f"  {category}: {result}")
            
            # Test classification
            test_email = "From: colleague@work.com\nSubject: Report\n\nPlease review the attached report."
            result = classifier.classify(test_email, return_all_scores=True)
            
            print(f"\nTest email classified as: {result.category}")
            print(f"Confidence: {result.confidence:.3f}")
            print(f"All scores: {result.all_scores}")
            
            # Show statistics
            print("\nFolder statistics:")
            stats = classifier.get_stats()
            for category, category_stats in stats.items():
                folder_path = classifier.get_folder_path(category)
                email_count = len(list(folder_path.glob("*.txt")))
                print(f"  {category:12}: {email_count} emails, {category_stats['word_count']} words")
    
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)


def advanced_multi_category_example():
    """Demonstrate advanced multi-category features."""
    print("\n=== Advanced Multi-Category Features ===")
    
    categories = ['urgent', 'routine', 'social', 'promotional']
    
    with MultiCategoryFilter(categories) as classifier:
        
        # Train with different types of content
        training_data = {
            'urgent': [
                "From: security@bank.com\nSubject: Security Alert\n\nSuspicious activity detected on your account.",
                "From: doctor@clinic.com\nSubject: Test Results\n\nYour test results are ready for review.",
                "From: boss@company.com\nSubject: URGENT: Client Issue\n\nClient is having a critical issue, please respond ASAP.",
            ],
            'routine': [
                "From: system@company.com\nSubject: Weekly Backup Report\n\nWeekly backup completed successfully.",
                "From: accounting@company.com\nSubject: Monthly Invoice\n\nYour monthly invoice is attached.",
                "From: calendar@system.com\nSubject: Meeting Reminder\n\nReminder: Team meeting tomorrow at 10 AM.",
            ],
            'social': [
                "From: friend@social.com\nSubject: Party Invitation\n\nYou're invited to my birthday party this Saturday!",
                "From: colleague@company.com\nSubject: Coffee?\n\nWant to grab coffee after work?",
                "From: neighbor@local.com\nSubject: Block Party\n\nNeighborhood block party this weekend.",
            ],
            'promotional': [
                "From: store@retail.com\nSubject: 50% Off Sale\n\nEverything 50% off this weekend only!",
                "From: airline@travel.com\nSubject: Flight Deals\n\nAmazing flight deals to Europe!",
                "From: restaurant@food.com\nSubject: New Menu Items\n\nTry our new seasonal menu items.",
            ]
        }
        
        # Train all categories
        print("Training categories...")
        for category, emails in training_data.items():
            result = classifier.train_category(category, emails)
            print(f"  {category}: {result.messages_processed} messages processed")
        
        # Test with ambiguous emails
        ambiguous_emails = [
            "From: boss@company.com\nSubject: Quick Question\n\nDo you have a minute to chat?",
            "From: store@shop.com\nSubject: Order Confirmation\n\nYour order has been confirmed.",
            "From: friend@email.com\nSubject: Emergency!\n\nCan you call me right away?",
        ]
        
        print("\nClassifying ambiguous emails:")
        for email in ambiguous_emails:
            result = classifier.classify(email, return_all_scores=True)
            print(f"\nEmail: {email.split('Subject: ')[1].split('\\n')[0]}")
            print(f"Classified as: {result.category} (confidence: {result.confidence:.3f})")
            
            # Show all scores sorted by probability
            sorted_scores = sorted(result.all_scores.items(), key=lambda x: x[1], reverse=True)
            print("  Score breakdown:")
            for cat, score in sorted_scores:
                print(f"    {cat:12}: {score:.3f}")
        
        # Demonstrate configuration saving/loading
        config_file = Path(tempfile.mktemp(suffix='.json'))
        try:
            classifier.save_configuration(config_file)
            print(f"\nConfiguration saved to: {config_file}")
            
            # Load configuration (would create new classifier)
            # loaded_classifier = MultiCategoryFilter.load_configuration(config_file)
            print("Configuration can be loaded to recreate classifier")
            
        finally:
            if config_file.exists():
                config_file.unlink()


def convenience_functions_example():
    """Demonstrate convenience functions."""
    print("\n=== Convenience Functions ===")
    
    # Quick classification without setting up full classifier
    categories = ['business', 'personal', 'marketing']
    email_content = "From: newsletter@company.com\nSubject: Monthly Newsletter\n\nOur monthly company newsletter."
    
    # Note: This would need pre-trained data to work effectively
    print("Using convenience function for quick classification:")
    print(f"Categories: {categories}")
    print(f"Email: {email_content.split('Subject: ')[1].split('\\n')[0]}")
    
    # In practice, you'd need to train the categories first
    print("(Note: Convenience functions work best with pre-trained categories)")


def email_routing_example():
    """Demonstrate practical email routing scenario."""
    print("\n=== Email Routing Example ===")
    
    class EmailRouter:
        """Example email router using multi-category classification."""
        
        def __init__(self):
            self.categories = ['inbox', 'work', 'social', 'promotions', 'spam']
            self.classifier = MultiCategoryFilter(self.categories)
            self.confidence_threshold = 0.6
        
        def route_email(self, email_content):
            """Route an email to appropriate folder."""
            result = self.classifier.classify(email_content, return_all_scores=True)
            
            # Only route if confidence is high enough
            if result.confidence >= self.confidence_threshold:
                folder = result.category
            else:
                folder = 'inbox'  # Default folder for uncertain emails
            
            return {
                'folder': folder,
                'confidence': result.confidence,
                'probability': result.probability,
                'all_scores': result.all_scores
            }
        
        def train_from_user_actions(self, email_content, user_folder):
            """Learn from user's folder placement."""
            self.classifier.train_category(user_folder, [email_content], force_update=True)
        
        def close(self):
            self.classifier.close()
    
    # Demonstrate email router
    router = EmailRouter()
    
    try:
        # Simulate some training (in practice, this would be from user actions)
        sample_training = {
            'work': ["From: boss@company.com\nSubject: Project\n\nProject update needed."],
            'social': ["From: friend@gmail.com\nSubject: Party\n\nParty this weekend!"],
            'promotions': ["From: store@shop.com\nSubject: Sale\n\n50% off everything!"],
            'spam': ["From: scam@bad.com\nSubject: FREE MONEY\n\nClick here for money!"],
        }
        
        for category, emails in sample_training.items():
            for email in emails:
                router.train_from_user_actions(email, category)
        
        # Test routing
        test_emails = [
            "From: colleague@work.com\nSubject: Meeting\n\nTeam meeting tomorrow.",
            "From: buddy@social.com\nSubject: Hangout\n\nWant to hang out this weekend?",
            "From: deals@store.com\nSubject: Special Offer\n\nLimited time special offer!",
        ]
        
        print("Email routing results:")
        for email in test_emails:
            routing = router.route_email(email)
            subject = email.split('Subject: ')[1].split('\\n')[0]
            print(f"  '{subject}' → {routing['folder']} (confidence: {routing['confidence']:.3f})")
    
    finally:
        router.close()


def main():
    """Run all multi-category examples."""
    print("MailProbe-Py Multi-Category Classification Examples")
    print("=" * 60)
    
    try:
        basic_multi_category_example()
        folder_based_classification_example()
        advanced_multi_category_example()
        convenience_functions_example()
        email_routing_example()
        
        print("\n" + "=" * 60)
        print("All multi-category examples completed successfully!")
        print("\nKey Features Demonstrated:")
        print("- Multi-category classification beyond spam/not-spam")
        print("- Folder-based automatic category discovery")
        print("- Advanced classification with confidence scoring")
        print("- Configuration saving and loading")
        print("- Practical email routing scenarios")
        print("- Integration with existing email workflows")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
