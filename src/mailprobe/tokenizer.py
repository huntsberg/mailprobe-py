"""
Email tokenizer for extracting words and phrases from email messages.

This module implements the tokenization logic similar to the original MailProbe,
extracting meaningful terms from email headers and body content.
"""

import re
import html
import base64
import quopri
from typing import List, Set, Dict, Iterator, Optional, Tuple
from urllib.parse import urlparse
from email.header import decode_header


class Token:
    """Represents a token extracted from an email message."""
    
    # Token flags (similar to original MailProbe)
    FLAG_WORD = 1
    FLAG_PHRASE = 2
    FLAG_HEADER = 4
    FLAG_BODY = 8
    FLAG_URL = 16
    FLAG_DERIVED = 32
    FLAG_ANY = 0xFFFF
    
    def __init__(self, text: str, flags: int = FLAG_WORD, prefix: str = "", count: int = 1):
        self.text = text
        self.flags = flags
        self.prefix = prefix
        self.count = count
        self.spam_count = 0
        self.good_count = 0
        self.probability = 0.5
    
    def get_key(self) -> str:
        """Get the database key for this token."""
        if self.prefix:
            return f"{self.prefix}_{self.text}"
        return self.text
    
    def is_phrase(self) -> bool:
        """Check if this token is a phrase (multiple words)."""
        return bool(self.flags & self.FLAG_PHRASE)
    
    def is_header(self) -> bool:
        """Check if this token came from email headers."""
        return bool(self.flags & self.FLAG_HEADER)
    
    def is_url(self) -> bool:
        """Check if this token is a URL."""
        return bool(self.flags & self.FLAG_URL)
    
    def __str__(self) -> str:
        return f"Token({self.get_key()}, count={self.count}, prob={self.probability:.3f})"
    
    def __repr__(self) -> str:
        return self.__str__()


class EmailTokenizer:
    """
    Tokenizes email messages to extract words and phrases for spam analysis.
    
    This class implements tokenization logic similar to the original MailProbe,
    including support for:
    - Header tokenization with prefixes
    - HTML tag removal and URL extraction
    - MIME decoding
    - Multi-word phrase generation
    - Character normalization
    """
    
    def __init__(self, 
                 max_phrase_terms: int = 2,
                 min_phrase_terms: int = 1,
                 min_term_length: int = 3,
                 max_term_length: int = 40,
                 remove_html: bool = True,
                 ignore_body: bool = False,
                 replace_non_ascii: str = 'z'):
        """
        Initialize the tokenizer with configuration options.
        
        Args:
            max_phrase_terms: Maximum number of words in a phrase
            min_phrase_terms: Minimum number of words in a phrase  
            min_term_length: Minimum length of individual terms
            max_term_length: Maximum length of individual terms
            remove_html: Whether to remove HTML tags from content
            ignore_body: Whether to ignore message body content
            replace_non_ascii: Character to replace non-ASCII chars with
        """
        self.max_phrase_terms = max_phrase_terms
        self.min_phrase_terms = min_phrase_terms
        self.min_term_length = min_term_length
        self.max_term_length = max_term_length
        self.remove_html = remove_html
        self.ignore_body = ignore_body
        self.replace_non_ascii = replace_non_ascii
        
        # Header prefixes for different types of headers
        self.header_prefixes = {
            'from': 'HFrom',
            'to': 'HTo', 
            'cc': 'HCc',
            'bcc': 'HBcc',
            'subject': 'HSubject',
            'received': 'HReceived',
            'reply-to': 'HReplyTo',
            'sender': 'HSender',
            'x-mailer': 'HXMailer',
            'user-agent': 'HUserAgent',
            'message-id': 'HMessageId',
            'references': 'HReferences',
            'in-reply-to': 'HInReplyTo',
        }
        
        # Compile regex patterns
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for tokenization."""
        # Word boundary pattern - letters, numbers, some punctuation
        self.word_pattern = re.compile(r'[a-zA-Z0-9_\-\.]+')
        
        # HTML tag pattern
        self.html_tag_pattern = re.compile(r'<[^>]*>')
        
        # URL pattern (simplified)
        self.url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+|'
            r'www\.[^\s<>"{}|\\^`\[\]]+|'
            r'[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}[^\s<>"{}|\\^`\[\]]*'
        )
        
        # Email pattern
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # Whitespace normalization
        self.whitespace_pattern = re.compile(r'\s+')
    
    def tokenize_message(self, message) -> List[Token]:
        """
        Tokenize an email message and return list of tokens.
        
        Args:
            message: EmailMessage object to tokenize
            
        Returns:
            List of Token objects extracted from the message
        """
        tokens = []
        
        # Tokenize headers
        for header_name, header_value in message.headers.items():
            header_tokens = self._tokenize_header(header_name.lower(), header_value)
            tokens.extend(header_tokens)
        
        # Tokenize body (if not ignored)
        if not self.ignore_body and message.body:
            body_tokens = self._tokenize_body(message.body)
            tokens.extend(body_tokens)
        
        # Generate phrases from word tokens
        phrase_tokens = self._generate_phrases(tokens)
        tokens.extend(phrase_tokens)
        
        return tokens
    
    def _tokenize_header(self, header_name: str, header_value: str) -> List[Token]:
        """Tokenize a specific email header."""
        tokens = []
        
        # Decode header if needed
        decoded_value = self._decode_header(header_value)
        
        # Get prefix for this header type
        prefix = self.header_prefixes.get(header_name, f"H{header_name.title()}")
        
        # Special handling for received headers
        if header_name == 'received':
            # Extract hostnames and IPs from received headers
            tokens.extend(self._tokenize_received_header(decoded_value, prefix))
        else:
            # Regular tokenization
            words = self._extract_words(decoded_value)
            for word in words:
                if self._is_valid_term(word):
                    token = Token(
                        text=self._normalize_term(word),
                        flags=Token.FLAG_WORD | Token.FLAG_HEADER,
                        prefix=prefix
                    )
                    tokens.append(token)
        
        return tokens
    
    def _tokenize_body(self, body: str) -> List[Token]:
        """Tokenize email body content."""
        tokens = []
        
        # Decode body content if needed
        decoded_body = self._decode_body(body)
        
        # Extract URLs first (before HTML removal)
        url_tokens = self._extract_urls(decoded_body)
        tokens.extend(url_tokens)
        
        # Remove HTML if configured
        if self.remove_html:
            decoded_body = self._remove_html(decoded_body)
        
        # Extract words from body
        words = self._extract_words(decoded_body)
        for word in words:
            if self._is_valid_term(word):
                token = Token(
                    text=self._normalize_term(word),
                    flags=Token.FLAG_WORD | Token.FLAG_BODY
                )
                tokens.append(token)
        
        return tokens
    
    def _tokenize_received_header(self, header_value: str, prefix: str) -> List[Token]:
        """Special tokenization for Received headers to extract hostnames."""
        tokens = []
        
        # Extract hostnames and IP addresses
        hostname_pattern = re.compile(r'\b([a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}\b')
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        
        # Find hostnames
        for match in hostname_pattern.finditer(header_value):
            hostname = match.group().lower()
            if len(hostname) >= self.min_term_length:
                token = Token(
                    text=hostname,
                    flags=Token.FLAG_WORD | Token.FLAG_HEADER,
                    prefix=prefix
                )
                tokens.append(token)
        
        # Find IP addresses
        for match in ip_pattern.finditer(header_value):
            ip = match.group()
            token = Token(
                text=ip,
                flags=Token.FLAG_WORD | Token.FLAG_HEADER,
                prefix=prefix
            )
            tokens.append(token)
        
        return tokens
    
    def _extract_urls(self, text: str) -> List[Token]:
        """Extract URLs from text content."""
        tokens = []
        
        for match in self.url_pattern.finditer(text):
            url = match.group()
            
            # Parse URL to extract meaningful parts
            try:
                parsed = urlparse(url if url.startswith('http') else f'http://{url}')
                
                # Add domain as token
                if parsed.netloc:
                    domain = parsed.netloc.lower()
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    
                    token = Token(
                        text=domain,
                        flags=Token.FLAG_URL | Token.FLAG_BODY,
                        prefix="URL"
                    )
                    tokens.append(token)
                
                # Add path components as tokens
                if parsed.path and len(parsed.path) > 1:
                    path_parts = [p for p in parsed.path.split('/') if p and len(p) >= self.min_term_length]
                    for part in path_parts[:3]:  # Limit to first 3 path components
                        token = Token(
                            text=self._normalize_term(part),
                            flags=Token.FLAG_URL | Token.FLAG_BODY,
                            prefix="URLPath"
                        )
                        tokens.append(token)
                        
            except Exception:
                # If URL parsing fails, just use the raw URL
                if len(url) >= self.min_term_length and len(url) <= self.max_term_length:
                    token = Token(
                        text=self._normalize_term(url),
                        flags=Token.FLAG_URL | Token.FLAG_BODY,
                        prefix="URL"
                    )
                    tokens.append(token)
        
        return tokens
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract individual words from text."""
        words = []
        
        for match in self.word_pattern.finditer(text):
            word = match.group()
            if len(word) >= self.min_term_length and len(word) <= self.max_term_length:
                words.append(word)
        
        return words
    
    def _generate_phrases(self, tokens: List[Token]) -> List[Token]:
        """Generate multi-word phrases from word tokens."""
        if self.max_phrase_terms <= 1:
            return []
        
        phrase_tokens = []
        
        # Group tokens by type (header prefix or body)
        token_groups = {}
        for token in tokens:
            if token.flags & Token.FLAG_WORD:
                key = token.prefix if token.prefix else "body"
                if key not in token_groups:
                    token_groups[key] = []
                token_groups[key].append(token)
        
        # Generate phrases within each group
        for group_tokens in token_groups.values():
            if len(group_tokens) < self.min_phrase_terms:
                continue
                
            for i in range(len(group_tokens)):
                for phrase_len in range(self.min_phrase_terms, min(self.max_phrase_terms + 1, len(group_tokens) - i + 1)):
                    if phrase_len == 1:
                        continue  # Skip single words
                    
                    phrase_words = []
                    phrase_prefix = None
                    phrase_flags = Token.FLAG_PHRASE
                    
                    for j in range(phrase_len):
                        token = group_tokens[i + j]
                        phrase_words.append(token.text)
                        if phrase_prefix is None:
                            phrase_prefix = token.prefix
                        if token.flags & Token.FLAG_HEADER:
                            phrase_flags |= Token.FLAG_HEADER
                        if token.flags & Token.FLAG_BODY:
                            phrase_flags |= Token.FLAG_BODY
                    
                    phrase_text = " ".join(phrase_words)
                    phrase_token = Token(
                        text=phrase_text,
                        flags=phrase_flags,
                        prefix=phrase_prefix
                    )
                    phrase_tokens.append(phrase_token)
        
        return phrase_tokens
    
    def _decode_header(self, header_value: str) -> str:
        """Decode RFC 2047 encoded email headers."""
        try:
            decoded_parts = decode_header(header_value)
            decoded_text = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_text += part.decode(encoding, errors='ignore')
                    else:
                        decoded_text += part.decode('ascii', errors='ignore')
                else:
                    decoded_text += part
            
            return decoded_text
        except Exception:
            return header_value
    
    def _decode_body(self, body: str) -> str:
        """Decode email body content (base64, quoted-printable, etc.)."""
        # This is a simplified version - in practice, you'd need to handle
        # MIME multipart messages and different encodings properly
        try:
            # Try base64 decode
            if body.replace('\n', '').replace('\r', '').replace(' ', '').isalnum():
                try:
                    decoded = base64.b64decode(body).decode('utf-8', errors='ignore')
                    if decoded.isprintable():
                        return decoded
                except Exception:
                    pass
            
            # Try quoted-printable decode
            try:
                decoded = quopri.decodestring(body).decode('utf-8', errors='ignore')
                if '=' not in body or decoded != body:
                    return decoded
            except Exception:
                pass
            
            return body
        except Exception:
            return body
    
    def _remove_html(self, text: str) -> str:
        """Remove HTML tags from text content."""
        # Remove HTML tags
        text = self.html_tag_pattern.sub(' ', text)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Normalize whitespace
        text = self.whitespace_pattern.sub(' ', text)
        
        return text.strip()
    
    def _is_valid_term(self, term: str) -> bool:
        """Check if a term is valid for tokenization."""
        if len(term) < self.min_term_length or len(term) > self.max_term_length:
            return False
        
        # Must contain at least one letter or number
        if not re.search(r'[a-zA-Z0-9]', term):
            return False
        
        return True
    
    def _normalize_term(self, term: str) -> str:
        """Normalize a term for consistent storage."""
        # Convert to lowercase
        term = term.lower()
        
        # Replace non-ASCII characters if configured
        if self.replace_non_ascii and self.replace_non_ascii != -1:
            term = re.sub(r'[^\x00-\x7F]', self.replace_non_ascii, term)
        
        return term
