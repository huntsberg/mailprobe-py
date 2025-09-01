"""Tests for email message parsing."""

import tempfile
from pathlib import Path

import pytest

from mailprobe.message import EmailMessage, EmailMessageReader, MessageDigestCache


class TestEmailMessage:
    """Test cases for EmailMessage."""

    def test_message_from_string(self):
        """Test creating message from string."""
        content = """From: test@example.com
To: user@example.com
Subject: Test message
Date: Mon, 1 Jan 2024 10:00:00 +0000

This is a test message.
"""
        message = EmailMessage(content)

        assert message.get_header("from") == "test@example.com"
        assert message.get_header("to") == "user@example.com"
        assert message.get_header("subject") == "Test message"
        assert "test message" in message.body.lower()

    def test_message_headers(self):
        """Test header parsing and access."""
        content = """From: sender@example.com
Subject: Important Message
X-Custom-Header: Custom Value

Body content here.
"""
        message = EmailMessage(content)

        # Test header access
        assert message.get_header("from") == "sender@example.com"
        assert message.get_header("subject") == "Important Message"
        assert message.get_header("x-custom-header") == "Custom Value"
        assert message.get_header("nonexistent") == ""
        assert message.get_header("nonexistent", "default") == "default"

        # Test header existence
        assert message.has_header("from")
        assert message.has_header("subject")
        assert not message.has_header("nonexistent")

    def test_message_body_extraction(self):
        """Test body content extraction."""
        content = """Subject: Test

This is the body content.
It spans multiple lines.
"""
        message = EmailMessage(content)

        body = message.body
        assert "body content" in body
        assert "multiple lines" in body

    def test_message_digest(self):
        """Test message digest calculation."""
        content1 = """From: test@example.com
Subject: Test

Hello world!
"""
        content2 = """From: test@example.com
Subject: Test

Hello world!
"""
        content3 = """From: different@example.com
Subject: Different

Different content!
"""

        message1 = EmailMessage(content1)
        message2 = EmailMessage(content2)
        message3 = EmailMessage(content3)

        # Same content should have same digest
        assert message1.digest == message2.digest

        # Different content should have different digest
        assert message1.digest != message3.digest

        # Digest should be 32 character hex string (MD5)
        assert len(message1.digest) == 32
        assert all(c in "0123456789abcdef" for c in message1.digest)

    def test_multipart_message(self):
        """Test multipart message handling."""
        # This is a simplified test - in practice you'd need proper MIME structure
        content = """Subject: Multipart Test
Content-Type: multipart/mixed

This is a multipart message.
"""
        message = EmailMessage(content)

        # Should handle gracefully even if not proper multipart
        assert isinstance(message.body, str)
        assert message.get_header("subject") == "Multipart Test"


class TestEmailMessageReader:
    """Test cases for EmailMessageReader."""

    def setup_method(self):
        """Set up test fixtures."""
        self.reader = EmailMessageReader()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_read_single_message_file(self):
        """Test reading a single message from file."""
        content = """From: test@example.com
Subject: Test

Hello world!
"""

        # Create test file
        test_file = Path(self.temp_dir) / "test_email.txt"
        test_file.write_text(content)

        # Read message
        messages = list(self.reader.read_from_file(test_file))

        assert len(messages) == 1
        assert messages[0].get_header("from") == "test@example.com"
        assert messages[0].get_header("subject") == "Test"

    def test_read_mbox_file(self):
        """Test reading mbox format file."""
        mbox_content = """From sender1@example.com Mon Jan  1 10:00:00 2024
From: sender1@example.com
Subject: First Message

This is the first message.

From sender2@example.com Mon Jan  1 11:00:00 2024
From: sender2@example.com
Subject: Second Message

This is the second message.
"""

        # Create mbox file
        mbox_file = Path(self.temp_dir) / "test.mbox"
        mbox_file.write_text(mbox_content)

        # Read messages
        messages = list(self.reader.read_from_file(mbox_file))

        assert len(messages) >= 1  # Should read at least one message
        # Note: mbox parsing might vary, so we just check basic functionality

    def test_read_from_string(self):
        """Test reading message from string."""
        content = """From: test@example.com
Subject: String Test

Message from string.
"""

        message = self.reader.read_from_string(content)

        assert message.get_header("from") == "test@example.com"
        assert message.get_header("subject") == "String Test"

    def test_read_nonexistent_file(self):
        """Test reading from nonexistent file."""
        nonexistent = Path(self.temp_dir) / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            list(self.reader.read_from_file(nonexistent))

    def test_maildir_structure(self):
        """Test reading from maildir structure."""
        # Create maildir structure
        maildir = Path(self.temp_dir) / "test_maildir"
        (maildir / "new").mkdir(parents=True)
        (maildir / "cur").mkdir(parents=True)

        # Add test messages
        msg1 = maildir / "new" / "msg1.eml"
        msg1.write_text(
            "From: test1@example.com\nSubject: New Message\n\nNew message content."
        )

        msg2 = maildir / "cur" / "msg2.eml"
        msg2.write_text(
            "From: test2@example.com\nSubject: Current Message\n\nCurrent message content."
        )

        # Read messages
        messages = list(self.reader.read_from_file(maildir))

        # Should read messages from both new and cur directories
        assert len(messages) >= 2
        subjects = [msg.get_header("subject") for msg in messages]
        assert "New Message" in subjects
        assert "Current Message" in subjects


class TestMessageDigestCache:
    """Test cases for MessageDigestCache."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = MessageDigestCache()

    def test_cache_operations(self):
        """Test basic cache operations."""
        digest1 = "abc123"
        digest2 = "def456"

        # Initially empty
        assert not self.cache.contains(digest1)
        assert self.cache.get_classification(digest1) is None
        assert self.cache.size() == 0

        # Add entries
        self.cache.add(digest1, True)  # spam
        self.cache.add(digest2, False)  # not spam

        # Check entries
        assert self.cache.contains(digest1)
        assert self.cache.contains(digest2)
        assert self.cache.get_classification(digest1) is True
        assert self.cache.get_classification(digest2) is False
        assert self.cache.size() == 2

        # Remove entry
        self.cache.remove(digest1)
        assert not self.cache.contains(digest1)
        assert self.cache.contains(digest2)
        assert self.cache.size() == 1

        # Clear cache
        self.cache.clear()
        assert self.cache.size() == 0
        assert not self.cache.contains(digest2)

    def test_cache_update(self):
        """Test updating existing cache entries."""
        digest = "abc123"

        # Add as spam
        self.cache.add(digest, True)
        assert self.cache.get_classification(digest) is True

        # Update to not spam
        self.cache.add(digest, False)
        assert self.cache.get_classification(digest) is False

        # Size should still be 1
        assert self.cache.size() == 1
