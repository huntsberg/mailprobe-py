"""
Email message parsing and handling.

This module provides classes for parsing and representing email messages,
including support for various mailbox formats and MIME decoding.
"""

import email
import email.policy
import hashlib
import re
from email.message import EmailMessage as StdEmailMessage
from pathlib import Path
from typing import Dict, List, Optional, Union, Iterator, TextIO
import mailbox

from .utils import safe_open_text, normalize_path


class EmailMessage:
    """
    Represents an email message for spam analysis.

    This class wraps Python's email.message.EmailMessage and provides
    additional functionality needed for email classifiering, including:
    - Message digest calculation for duplicate detection
    - Header normalization and extraction
    - Body content extraction and decoding
    - MIME attachment handling
    """

    def __init__(self, raw_message: Union[str, bytes, StdEmailMessage]):
        """
        Initialize EmailMessage from raw message data.

        Args:
            raw_message: Raw email message as string, bytes, or EmailMessage
        """
        if isinstance(raw_message, StdEmailMessage):
            self._message = raw_message
        else:
            if isinstance(raw_message, bytes):
                raw_message = raw_message.decode("utf-8", errors="ignore")

            # Parse the message using email library
            self._message = email.message_from_string(
                raw_message, policy=email.policy.default
            )

        self._digest: Optional[str] = None
        self._headers: Optional[Dict[str, str]] = None
        self._body: Optional[str] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get normalized email headers as a dictionary."""
        if self._headers is None:
            self._headers = {}

            for key, value in self._message.items():
                # Normalize header names to lowercase
                normalized_key = key.lower()

                # Handle multiple headers with same name
                if normalized_key in self._headers:
                    self._headers[normalized_key] += f" {value}"
                else:
                    self._headers[normalized_key] = value

        return self._headers

    @property
    def body(self) -> str:
        """Get the email body content as plain text."""
        if self._body is None:
            self._body = self._extract_body()
        return self._body

    @property
    def digest(self) -> str:
        """Get MD5 digest of the message for duplicate detection."""
        if self._digest is None:
            self._digest = self._calculate_digest()
        return self._digest

    def _extract_body(self) -> str:
        """Extract plain text body from the email message."""
        body_parts = []

        if self._message.is_multipart():
            # Handle multipart messages
            for part in self._message.walk():
                if part.get_content_type() == "text/plain":
                    content = part.get_content()
                    if isinstance(content, str):
                        body_parts.append(content)
                elif part.get_content_type() == "text/html":
                    # Include HTML content but it will be processed by tokenizer
                    content = part.get_content()
                    if isinstance(content, str):
                        body_parts.append(content)
        else:
            # Single part message
            if self._message.get_content_type().startswith("text/"):
                content = self._message.get_content()
                if isinstance(content, str):
                    body_parts.append(content)

        return "\n".join(body_parts)

    def _calculate_digest(self) -> str:
        """Calculate MD5 digest of the message for duplicate detection."""
        # Use a normalized version of the message for digest calculation
        # This helps identify the same message even if headers change slightly

        # Get key headers for digest
        key_headers = ["from", "to", "subject", "date", "message-id"]
        digest_content = []

        for header in key_headers:
            value = self.headers.get(header, "")
            if value:
                # Normalize whitespace and case
                normalized = re.sub(r"\s+", " ", value.strip().lower())
                digest_content.append(f"{header}:{normalized}")

        # Add body content (first 1000 chars to avoid huge digests)
        body = self.body[:1000] if self.body else ""
        body_normalized = re.sub(r"\s+", " ", body.strip().lower())
        digest_content.append(f"body:{body_normalized}")

        # Calculate MD5 hash
        content_str = "\n".join(digest_content)
        return hashlib.md5(content_str.encode("utf-8")).hexdigest()

    def get_header(self, name: str, default: str = "") -> str:
        """Get a specific header value."""
        return self.headers.get(name.lower(), default)

    def has_header(self, name: str) -> bool:
        """Check if a header exists."""
        return name.lower() in self.headers

    def __str__(self) -> str:
        return f"EmailMessage(digest={self.digest[:8]}..., subject={self.get_header('subject', 'No Subject')[:50]})"

    def __repr__(self) -> str:
        return self.__str__()


class EmailMessageReader:
    """
    Reads email messages from various sources and formats.

    Supports:
    - Individual email files
    - mbox format mailboxes
    - Maildir format mailboxes
    - Raw message strings
    """

    def __init__(self, ignore_from: bool = False, ignore_content_length: bool = False):
        """
        Initialize the message reader.

        Args:
            ignore_from: Whether to ignore From_ lines in mbox format
            ignore_content_length: Whether to ignore Content-Length headers
        """
        self.ignore_from = ignore_from
        self.ignore_content_length = ignore_content_length

    def read_from_file(self, filepath: Union[str, Path]) -> Iterator[EmailMessage]:
        """
        Read messages from a file.

        Args:
            filepath: Path to the email file or mailbox

        Yields:
            EmailMessage objects
        """
        filepath = normalize_path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        if filepath.is_dir():
            # Assume Maildir format
            yield from self._read_maildir(filepath)
        else:
            # Try to determine format by content
            with safe_open_text(filepath) as f:
                content = f.read()

            if self._is_mbox_format(content):
                yield from self._read_mbox_file(filepath)
            else:
                # Treat as single message
                yield EmailMessage(content)

    def read_from_string(self, content: str) -> EmailMessage:
        """
        Read a single message from a string.

        Args:
            content: Raw email message content

        Returns:
            EmailMessage object
        """
        return EmailMessage(content)

    def read_from_stdin(self) -> EmailMessage:
        """
        Read a single message from standard input.

        Returns:
            EmailMessage object
        """
        import sys

        content = sys.stdin.read()
        return EmailMessage(content)

    def _read_mbox_file(self, filepath: Path) -> Iterator[EmailMessage]:
        """Read messages from an mbox format file."""
        try:
            mbox = mailbox.mbox(str(filepath))
            for message in mbox:
                yield EmailMessage(message)
        except Exception as e:
            # Fallback to manual parsing if mailbox module fails
            yield from self._read_mbox_manual(filepath)

    def _read_mbox_manual(self, filepath: Path) -> Iterator[EmailMessage]:
        """Manually parse mbox format file."""
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            current_message = []
            in_message = False

            for line in f:
                if line.startswith("From ") and not self.ignore_from:
                    # Start of new message
                    if in_message and current_message:
                        # Yield previous message
                        message_content = "".join(current_message)
                        yield EmailMessage(message_content)

                    # Start new message
                    current_message = []
                    in_message = True
                elif in_message:
                    current_message.append(line)
                elif not in_message and line.strip():
                    # First non-empty line, start message
                    current_message = [line]
                    in_message = True

            # Yield last message
            if in_message and current_message:
                message_content = "".join(current_message)
                yield EmailMessage(message_content)

    def _read_maildir(self, maildir_path: Path) -> Iterator[EmailMessage]:
        """Read messages from a Maildir format directory."""
        try:
            maildir = mailbox.Maildir(str(maildir_path))
            for message in maildir:
                yield EmailMessage(message)
        except Exception:
            # Fallback to manual reading
            for subdir in ["new", "cur"]:
                subdir_path = maildir_path / subdir
                if subdir_path.exists():
                    for msg_file in subdir_path.iterdir():
                        if msg_file.is_file() and not msg_file.name.startswith("."):
                            try:
                                with safe_open_text(msg_file) as f:
                                    content = f.read()
                                yield EmailMessage(content)
                            except Exception:
                                continue

    def _is_mbox_format(self, content: str) -> bool:
        """Check if content appears to be in mbox format."""
        lines = content.split("\n")

        # Look for From_ lines that indicate mbox format
        from_lines = 0
        for line in lines[:20]:  # Check first 20 lines
            if line.startswith("From ") and "@" in line:
                from_lines += 1

        # If we find multiple From_ lines, it's likely mbox
        return from_lines > 1 or (from_lines == 1 and len(lines) > 50)


class MessageDigestCache:
    """
    Cache for message digests to track which messages have been processed.

    This helps avoid reprocessing the same message multiple times and
    enables proper reclassification of messages.
    """

    def __init__(self):
        self._cache: Dict[str, bool] = {}  # digest -> is_spam

    def contains(self, digest: str) -> bool:
        """Check if a message digest is in the cache."""
        return digest in self._cache

    def get_classification(self, digest: str) -> Optional[bool]:
        """Get the spam classification for a message digest."""
        return self._cache.get(digest)

    def add(self, digest: str, is_spam: bool) -> None:
        """Add a message digest to the cache with its classification."""
        self._cache[digest] = is_spam

    def remove(self, digest: str) -> None:
        """Remove a message digest from the cache."""
        self._cache.pop(digest, None)

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()

    def size(self) -> int:
        """Get the number of entries in the cache."""
        return len(self._cache)
