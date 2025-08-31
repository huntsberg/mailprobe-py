# Multi-Category Classification Guide

MailProbe-Py supports advanced multi-category classification that goes beyond simple spam/not-spam detection. You can classify emails into multiple custom categories such as different folders, priority levels, or any classification scheme that suits your needs.

## Overview

The multi-category system allows you to:

- **Classify emails into multiple categories** (work, personal, newsletters, etc.)
- **Automatically discover categories from folder structures**
- **Train on different corpuses for different purposes**
- **Use confidence scoring** for reliable classification
- **Integrate with existing email workflows**

## Quick Start

### Basic Multi-Category Classification

```python
from spamprobe import MultiCategoryFilter

# Define your categories
categories = ['work', 'personal', 'newsletters', 'spam']

# Create classifier
with MultiCategoryFilter(categories) as classifier:
    # Train on different types of emails
    work_emails = [
        "From: boss@company.com\nSubject: Meeting\n\nTeam meeting tomorrow.",
        "From: client@business.com\nSubject: Project\n\nProject update needed."
    ]
    
    personal_emails = [
        "From: friend@gmail.com\nSubject: Lunch\n\nWant to grab lunch?",
        "From: family@home.com\nSubject: Visit\n\nComing to visit soon."
    ]
    
    # Train categories
    classifier.train_category('work', work_emails)
    classifier.train_category('personal', personal_emails)
    
    # Classify new email
    new_email = "From: colleague@work.com\nSubject: Report\n\nPlease review the report."
    result = classifier.classify(new_email)
    
    print(f"Email should go to: {result.category}")
    print(f"Confidence: {result.confidence:.3f}")
```

### Folder-Based Classification

```python
from spamprobe import FolderBasedClassifier

# Organize emails in folders:
# emails/
#   ├── work/
#   ├── personal/
#   ├── newsletters/
#   └── spam/

# Auto-discover categories from folder structure
with FolderBasedClassifier('emails/') as classifier:
    # Train from all folders automatically
    results = classifier.train_from_folders()
    
    # Classify new email
    result = classifier.classify(new_email)
    print(f"Email should go to folder: {result.category}")
    
    # Optionally move email to appropriate folder
    if result.confidence > 0.7:
        new_path = classifier.move_email_to_folder(email_file, result.category)
```

## Core Classes

### MultiCategoryFilter

The main class for multi-category email classification.

#### Constructor

```python
MultiCategoryFilter(categories, database_path=None, config=None)
```

- `categories`: List of category names
- `database_path`: Path to database directory (default: `~/.mailprobe-py-multi`)
- `config`: FilterConfig object for customization

#### Training Methods

```python
# Train on specific category
result = classifier.train_category('work', email_list)

# Train with force update
result = classifier.train_category('spam', spam_emails, force_update=True)
```

#### Classification Methods

```python
# Simple classification
result = classifier.classify(email_content)
print(f"Category: {result.category}")

# Detailed classification with all scores
result = classifier.classify(email_content, return_all_scores=True)
print(f"All scores: {result.all_scores}")
```

#### Database Management

```python
# Get statistics for specific category
stats = classifier.get_category_stats('work')

# Get statistics for all categories
all_stats = classifier.get_all_stats()

# Cleanup old/rare words
removed = classifier.cleanup_category('work', max_count=2, max_age_days=7)
cleanup_results = classifier.cleanup_all_categories()

# Export/import category data
data = classifier.export_category('work')
imported_count = classifier.import_category('work', data)

# Save/load configuration
classifier.save_configuration('config.json')
loaded_classifier = MultiCategoryFilter.load_configuration('config.json')
```

### FolderBasedClassifier

Convenient classifier that automatically manages categories based on directory structure.

#### Constructor

```python
FolderBasedClassifier(base_path, database_path=None, config=None, exclude_folders=None)
```

- `base_path`: Directory containing category folders
- `database_path`: Path to database directory
- `config`: FilterConfig object
- `exclude_folders`: Folder names to exclude (default: `['.git', '.DS_Store', '__pycache__']`)

#### Methods

```python
# Auto-discover categories
categories = classifier.get_categories()

# Train from folder structure
results = classifier.train_from_folders()

# Get folder path for category
folder_path = classifier.get_folder_path('work')

# Move email to appropriate folder
new_path = classifier.move_email_to_folder(email_file, 'work')

# Classify and optionally move
result, moved_path = classifier.classify_and_move(email_file, confidence_threshold=0.7)
```

## Result Objects

### CategoryResult

Returned by classification methods:

```python
result = classifier.classify(email, return_all_scores=True)

print(f"Category: {result.category}")           # Best matching category
print(f"Probability: {result.probability}")     # Probability for best category (0.0-1.0)
print(f"Confidence: {result.confidence}")       # Confidence in classification (0.0-1.0)
print(f"All scores: {result.all_scores}")       # Dict of all category scores
```

### CategoryTrainingResult

Returned by training methods:

```python
result = classifier.train_category('work', emails)

print(f"Category: {result.category}")                    # Category that was trained
print(f"Messages processed: {result.messages_processed}") # Number of messages processed
print(f"Messages updated: {result.messages_updated}")     # Number that updated database
print(f"Database updated: {result.database_updated}")     # Whether database changed
```

## Advanced Usage

### Custom Categories for Different Use Cases

#### Priority-Based Classification

```python
# Classify by urgency/priority
priorities = ['urgent', 'high', 'normal', 'low']

with MultiCategoryFilter(priorities) as classifier:
    # Train on emails with different priority indicators
    urgent_emails = [
        "From: security@bank.com\nSubject: Security Alert\n\nSuspicious activity detected.",
        "From: boss@company.com\nSubject: URGENT: Client Issue\n\nClient emergency!"
    ]
    
    normal_emails = [
        "From: newsletter@site.com\nSubject: Weekly Update\n\nThis week's news.",
        "From: system@company.com\nSubject: Backup Complete\n\nBackup finished successfully."
    ]
    
    classifier.train_category('urgent', urgent_emails)
    classifier.train_category('normal', normal_emails)
```

#### Department-Based Classification

```python
# Classify by department/team
departments = ['engineering', 'marketing', 'sales', 'hr', 'finance']

with MultiCategoryFilter(departments) as classifier:
    # Train on emails from different departments
    engineering_emails = [
        "From: dev@company.com\nSubject: Code Review\n\nPlease review my pull request.",
        "From: ops@company.com\nSubject: Server Maintenance\n\nScheduled maintenance tonight."
    ]
    
    marketing_emails = [
        "From: marketing@company.com\nSubject: Campaign Results\n\nQ4 campaign performance.",
        "From: social@company.com\nSubject: Social Media\n\nSocial media metrics report."
    ]
    
    classifier.train_category('engineering', engineering_emails)
    classifier.train_category('marketing', marketing_emails)
```

#### Content-Type Classification

```python
# Classify by content type
content_types = ['invoices', 'receipts', 'contracts', 'reports', 'correspondence']

with MultiCategoryFilter(content_types) as classifier:
    # Train on different document types
    invoices = [
        "From: billing@vendor.com\nSubject: Invoice #12345\n\nInvoice for services rendered.",
        "From: accounting@supplier.com\nSubject: Monthly Bill\n\nYour monthly statement."
    ]
    
    reports = [
        "From: analytics@company.com\nSubject: Weekly Report\n\nWeekly performance metrics.",
        "From: finance@company.com\nSubject: Financial Summary\n\nQuarterly financial report."
    ]
    
    classifier.train_category('invoices', invoices)
    classifier.train_category('reports', reports)
```

### Email Routing System

```python
class EmailRouter:
    """Advanced email routing system using multi-category classification."""
    
    def __init__(self, categories, confidence_threshold=0.6):
        self.classifier = MultiCategoryFilter(categories)
        self.confidence_threshold = confidence_threshold
        self.routing_rules = {}
    
    def add_routing_rule(self, category, action):
        """Add custom routing rule for a category."""
        self.routing_rules[category] = action
    
    def route_email(self, email_content):
        """Route email based on classification and rules."""
        result = self.classifier.classify(email_content, return_all_scores=True)
        
        # Apply confidence threshold
        if result.confidence < self.confidence_threshold:
            return {
                'action': 'manual_review',
                'reason': 'low_confidence',
                'category': result.category,
                'confidence': result.confidence
            }
        
        # Apply custom routing rules
        if result.category in self.routing_rules:
            action = self.routing_rules[result.category]
        else:
            action = f'move_to_{result.category}'
        
        return {
            'action': action,
            'category': result.category,
            'confidence': result.confidence,
            'all_scores': result.all_scores
        }
    
    def learn_from_user_action(self, email_content, user_category):
        """Learn from user's manual categorization."""
        self.classifier.train_category(user_category, [email_content], force_update=True)

# Usage
router = EmailRouter(['inbox', 'work', 'personal', 'spam'])
router.add_routing_rule('spam', 'delete')
router.add_routing_rule('work', 'move_to_work_folder')

routing = router.route_email(email_content)
print(f"Action: {routing['action']}")
```

### Batch Processing

```python
def process_email_batch(email_files, classifier):
    """Process multiple emails efficiently."""
    results = []
    
    for email_file in email_files:
        try:
            result = classifier.classify(email_file, return_all_scores=True)
            results.append({
                'file': email_file,
                'category': result.category,
                'confidence': result.confidence,
                'success': True
            })
        except Exception as e:
            results.append({
                'file': email_file,
                'error': str(e),
                'success': False
            })
    
    return results

# Usage
with MultiCategoryFilter(['work', 'personal', 'spam']) as classifier:
    # Train classifier first...
    
    # Process batch of emails
    email_files = ['email1.txt', 'email2.txt', 'email3.txt']
    results = process_email_batch(email_files, classifier)
    
    for result in results:
        if result['success']:
            print(f"{result['file']} → {result['category']} ({result['confidence']:.3f})")
        else:
            print(f"{result['file']} → ERROR: {result['error']}")
```

## Configuration and Tuning

### Custom Filter Configuration

```python
from spamprobe import FilterConfig

# Create custom configuration
config = FilterConfig(
    spam_threshold=0.8,        # Lower threshold for more sensitive classification
    min_word_count=3,          # Require fewer training examples
    terms_for_score=20,        # Use more terms for scoring
    max_phrase_terms=3,        # Allow longer phrases
    cache_size=5000           # Larger cache for better performance
)

classifier = MultiCategoryFilter(categories, config=config)
```

### Performance Tuning

```python
# For high-volume processing
config = FilterConfig(
    cache_size=10000,          # Large cache
    terms_for_score=10,        # Fewer terms for faster scoring
    min_word_count=2,          # Lower threshold for faster training
)

# For high accuracy
config = FilterConfig(
    spam_threshold=0.95,       # Higher threshold for more certainty
    min_word_count=10,         # More training data required
    terms_for_score=25,        # More terms for better accuracy
)
```

### Category-Specific Configuration

```python
# Different configurations for different categories
configs = {
    'spam': FilterConfig(spam_threshold=0.9, min_word_count=5),
    'work': FilterConfig(spam_threshold=0.8, min_word_count=3),
    'personal': FilterConfig(spam_threshold=0.7, min_word_count=2)
}

# Note: Current implementation uses single config for all categories
# This is a conceptual example for future enhancement
```

## Integration Examples

### Email Server Integration

```python
def process_incoming_email(email_content, classifier):
    """Process incoming email for server integration."""
    result = classifier.classify(email_content, return_all_scores=True)
    
    # Create email headers for downstream processing
    headers = {
        'X-MailProbe-Category': result.category,
        'X-MailProbe-Probability': f"{result.probability:.3f}",
        'X-MailProbe-Confidence': f"{result.confidence:.3f}"
    }
    
    # Add detailed scoring if needed
    if result.all_scores:
        for category, score in result.all_scores.items():
            headers[f'X-MailProbe-Score-{category}'] = f"{score:.3f}"
    
    return headers

# Usage with email server
with MultiCategoryFilter(['inbox', 'work', 'personal', 'spam']) as classifier:
    headers = process_incoming_email(email_content, classifier)
    # Add headers to email and route accordingly
```

### IMAP Integration

```python
import imaplib
import email

def classify_imap_folder(imap_server, folder, classifier):
    """Classify emails in IMAP folder."""
    imap_server.select(folder)
    
    # Get all messages
    _, message_ids = imap_server.search(None, 'ALL')
    
    for msg_id in message_ids[0].split():
        # Fetch message
        _, msg_data = imap_server.fetch(msg_id, '(RFC822)')
        email_message = email.message_from_bytes(msg_data[0][1])
        
        # Convert to string for classification
        email_content = str(email_message)
        
        # Classify
        result = classifier.classify(email_content)
        
        # Move to appropriate folder based on classification
        if result.confidence > 0.7:
            target_folder = f"INBOX.{result.category}"
            imap_server.move(msg_id, target_folder)

# Usage
# with imaplib.IMAP4_SSL('imap.gmail.com') as imap:
#     imap.login('user@gmail.com', 'password')
#     classify_imap_folder(imap, 'INBOX', classifier)
```

## Best Practices

### Training Data Quality

1. **Balanced Training**: Ensure each category has sufficient training examples
2. **Representative Samples**: Use emails that are typical of each category
3. **Regular Updates**: Retrain with new examples as email patterns change
4. **Quality Control**: Review misclassified emails and add them to training

### Category Design

1. **Mutually Exclusive**: Categories should be distinct and non-overlapping
2. **Meaningful Differences**: Categories should have clear linguistic differences
3. **Practical Utility**: Categories should serve a real organizational purpose
4. **Manageable Number**: Start with 3-5 categories, expand as needed

### Performance Optimization

1. **Cache Tuning**: Adjust cache size based on available memory
2. **Cleanup Regular**: Run database cleanup periodically
3. **Batch Processing**: Process multiple emails together when possible
4. **Confidence Thresholds**: Use appropriate thresholds for your use case

### Error Handling

```python
def robust_classification(classifier, email_content):
    """Robust classification with error handling."""
    try:
        result = classifier.classify(email_content, return_all_scores=True)
        
        # Check for low confidence
        if result.confidence < 0.5:
            return {
                'category': 'uncertain',
                'needs_review': True,
                'result': result
            }
        
        return {
            'category': result.category,
            'needs_review': False,
            'result': result
        }
        
    except Exception as e:
        return {
            'category': 'error',
            'needs_review': True,
            'error': str(e)
        }
```

## Troubleshooting

### Common Issues

1. **Low Classification Accuracy**
   - Increase training data for each category
   - Check for overlapping categories
   - Adjust spam threshold and other parameters

2. **Poor Confidence Scores**
   - Ensure categories are linguistically distinct
   - Add more diverse training examples
   - Consider merging similar categories

3. **Slow Performance**
   - Increase cache size
   - Reduce terms_for_score
   - Run database cleanup regularly

4. **Memory Usage**
   - Reduce cache size
   - Clean up old/rare words more aggressively
   - Process emails in smaller batches

### Debugging

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check category statistics
stats = classifier.get_all_stats()
for category, stat in stats.items():
    print(f"{category}: {stat['word_count']} words, {stat['total_message_count']} messages")

# Analyze classification details
result = classifier.classify(email, return_all_scores=True)
print(f"Classification: {result}")
print(f"Score breakdown: {result.all_scores}")
```

## Convenience Functions

For quick operations without setting up full classifiers:

```python
from spamprobe import classify_into_categories, train_from_folder_structure

# Quick classification
categories = ['work', 'personal', 'spam']
result = classify_into_categories(email_content, categories)

# Quick training from folders
results = train_from_folder_structure('emails/')
```

## Conclusion

The multi-category classification system in MailProbe-Py provides powerful and flexible email organization capabilities. Whether you need simple folder-based routing or complex multi-dimensional classification, the system can be adapted to your specific needs while maintaining the accuracy and performance of the underlying Bayesian algorithm.
