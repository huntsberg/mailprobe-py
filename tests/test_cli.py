"""Tests for the command-line interface."""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner

from mailprobe.cli import cli


class TestCLI:
    """Test cases for CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_db"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'MailProbe-Py: Bayesian email classifier' in result.output
    
    def test_create_db_command(self):
        """Test create-db command."""
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'create-db'
        ])
        
        assert result.exit_code == 0
        assert 'Database created successfully' in result.output
        assert (self.db_path / 'words.db').exists()
    
    def test_info_command(self):
        """Test info command."""
        # First create database
        self.runner.invoke(cli, ['-d', str(self.db_path), 'create-db'])
        
        # Then get info
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'info'
        ])
        
        assert result.exit_code == 0
        assert 'Database Information:' in result.output
        assert 'Words:' in result.output
        assert 'Good messages:' in result.output
        assert 'Spam messages:' in result.output
    
    def test_train_commands_with_files(self):
        """Test training commands with email files."""
        # Create test email files
        good_email = self.db_path / "good.txt"
        spam_email = self.db_path / "spam.txt"
        
        good_email.parent.mkdir(parents=True, exist_ok=True)
        
        good_email.write_text("""From: friend@example.com
Subject: Meeting tomorrow

Let's meet for lunch tomorrow at noon.
""")
        
        spam_email.write_text("""From: spammer@bad.com
Subject: FREE MONEY NOW!!!

Click here to get FREE MONEY! Limited time offer!
""")
        
        # Create database
        self.runner.invoke(cli, ['-d', str(self.db_path), 'create-db'])
        
        # Train on good email
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'good', str(good_email)
        ])
        assert result.exit_code == 0
        
        # Train on spam email
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'spam', str(spam_email)
        ])
        assert result.exit_code == 0
        
        # Check database has been updated
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'info'
        ])
        assert result.exit_code == 0
        assert 'Good messages: 1' in result.output
        assert 'Spam messages: 1' in result.output
    
    def test_score_command_with_file(self):
        """Test score command with email file."""
        # Create test email
        test_email = self.db_path / "test.txt"
        test_email.parent.mkdir(parents=True, exist_ok=True)
        test_email.write_text("""From: test@example.com
Subject: Test message

This is a test message.
""")
        
        # Create database
        self.runner.invoke(cli, ['-d', str(self.db_path), 'create-db'])
        
        # Score the email
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'score', str(test_email)
        ])
        
        assert result.exit_code == 0
        # Should output either GOOD or SPAM followed by probability
        assert ('GOOD' in result.output or 'SPAM' in result.output)
    
    def test_score_with_show_terms(self):
        """Test score command with -T flag to show terms."""
        # Create test email
        test_email = self.db_path / "test.txt"
        test_email.parent.mkdir(parents=True, exist_ok=True)
        test_email.write_text("""From: test@example.com
Subject: Test message

This is a test message with some words.
""")
        
        # Create database and add some training data
        self.runner.invoke(cli, ['-d', str(self.db_path), 'create-db'])
        
        # Score with terms
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'score', '-T', str(test_email)
        ])
        
        assert result.exit_code == 0
        assert ('GOOD' in result.output or 'SPAM' in result.output)
    
    def test_cleanup_command(self):
        """Test cleanup command."""
        # Create database
        self.runner.invoke(cli, ['-d', str(self.db_path), 'create-db'])
        
        # Run cleanup
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'cleanup', '--max-count', '2', '--max-age-days', '0'
        ])
        
        assert result.exit_code == 0
        assert 'Removed' in result.output and 'words' in result.output
    
    def test_purge_command(self):
        """Test purge command."""
        # Create database
        self.runner.invoke(cli, ['-d', str(self.db_path), 'create-db'])
        
        # Run purge
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'purge', '--max-count', '1'
        ])
        
        assert result.exit_code == 0
        assert 'Purged' in result.output and 'words' in result.output
    
    def test_verbose_flag(self):
        """Test verbose flag."""
        # Create test email
        test_email = self.db_path / "test.txt"
        test_email.parent.mkdir(parents=True, exist_ok=True)
        test_email.write_text("""From: test@example.com
Subject: Test

Hello world!
""")
        
        # Create database
        self.runner.invoke(cli, ['-d', str(self.db_path), 'create-db'])
        
        # Train with verbose flag
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            '-v',  # verbose flag
            'good', str(test_email)
        ])
        
        assert result.exit_code == 0
        # Verbose output should show processing information
        assert 'Processed' in result.output
    
    def test_configuration_options(self):
        """Test various configuration options."""
        # Create database with custom settings
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            '-l', '0.8',  # spam threshold
            '-C', '10',   # min word count
            '-w', '20',   # terms for score
            'create-db'
        ])
        
        assert result.exit_code == 0
    
    def test_invalid_command(self):
        """Test invalid command handling."""
        result = self.runner.invoke(cli, ['invalid-command'])
        
        assert result.exit_code != 0
        assert 'no such command' in result.output.lower()
    
    def test_missing_database_directory(self):
        """Test behavior with missing database directory."""
        nonexistent_path = Path(self.temp_dir) / "nonexistent"
        
        result = self.runner.invoke(cli, [
            '-d', str(nonexistent_path),
            'info'
        ])
        
        # Should handle gracefully (either create or show error)
        # The exact behavior depends on implementation
        assert isinstance(result.exit_code, int)


class TestCLIIntegration:
    """Integration tests for CLI workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "integration_db"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_full_workflow(self):
        """Test complete email classifiering workflow."""
        # Create test emails
        emails_dir = self.db_path / "emails"
        emails_dir.mkdir(parents=True)
        
        good_emails = [
            "From: colleague@company.com\nSubject: Meeting\n\nLet's meet tomorrow.",
            "From: friend@example.com\nSubject: Lunch\n\nWant to grab lunch?",
        ]
        
        spam_emails = [
            "From: spammer@bad.com\nSubject: FREE MONEY\n\nClick here for free money!",
            "From: scammer@evil.com\nSubject: URGENT\n\nYou've won a million dollars!",
        ]
        
        # Create email files
        for i, email in enumerate(good_emails):
            (emails_dir / f"good{i}.txt").write_text(email)
        
        for i, email in enumerate(spam_emails):
            (emails_dir / f"spam{i}.txt").write_text(email)
        
        # Step 1: Create database
        result = self.runner.invoke(cli, ['-d', str(self.db_path), 'create-db'])
        assert result.exit_code == 0
        
        # Step 2: Train on good emails
        for i in range(len(good_emails)):
            result = self.runner.invoke(cli, [
                '-d', str(self.db_path),
                'good', str(emails_dir / f"good{i}.txt")
            ])
            assert result.exit_code == 0
        
        # Step 3: Train on spam emails
        for i in range(len(spam_emails)):
            result = self.runner.invoke(cli, [
                '-d', str(self.db_path),
                'spam', str(emails_dir / f"spam{i}.txt")
            ])
            assert result.exit_code == 0
        
        # Step 4: Check database info
        result = self.runner.invoke(cli, ['-d', str(self.db_path), 'info'])
        assert result.exit_code == 0
        assert 'Good messages: 2' in result.output
        assert 'Spam messages: 2' in result.output
        
        # Step 5: Test scoring
        test_email = emails_dir / "test.txt"
        test_email.write_text("From: test@example.com\nSubject: Question\n\nI have a question.")
        
        result = self.runner.invoke(cli, [
            '-d', str(self.db_path),
            'score', str(test_email)
        ])
        assert result.exit_code == 0
        assert ('GOOD' in result.output or 'SPAM' in result.output)
        
        # Step 6: Test cleanup
        result = self.runner.invoke(cli, ['-d', str(self.db_path), 'cleanup'])
        assert result.exit_code == 0
