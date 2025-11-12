"""Content cleaning and normalization."""

import re
import logging
from typing import Dict, Any
from bs4 import BeautifulSoup
import unicodedata


class ContentCleaner:
    """Clean and normalize content."""

    def __init__(self):
        """Initialize content cleaner."""
        self.logger = logging.getLogger(__name__)

    def clean(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean all text fields in content.

        Args:
            content: Content dictionary

        Returns:
            Cleaned content dictionary
        """
        try:
            cleaned = content.copy()

            # Clean title
            if "title" in cleaned:
                cleaned["title"] = self.clean_text(cleaned["title"])

            # Clean body
            if "body" in cleaned:
                cleaned["body"] = self.clean_text(cleaned["body"], preserve_paragraphs=True)

            return cleaned

        except Exception as e:
            self.logger.error(f"Error cleaning content: {e}")
            return content

    def clean_text(self, text: str, preserve_paragraphs: bool = False) -> str:
        """
        Clean and normalize text.

        Args:
            text: Raw text
            preserve_paragraphs: Whether to preserve paragraph structure

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove HTML tags
        text = self.remove_html(text)

        # Normalize Unicode
        text = self.normalize_unicode(text)

        # Remove special characters (but keep Hebrew, English, numbers, basic punctuation)
        text = self.remove_special_characters(text)

        # Normalize whitespace
        text = self.normalize_whitespace(text, preserve_paragraphs)

        return text.strip()

    def remove_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        try:
            soup = BeautifulSoup(text, "html.parser")
            return soup.get_text()
        except:
            # Fallback to regex if BeautifulSoup fails
            return re.sub(r"<[^>]+>", "", text)

    def normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode characters.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        # Normalize to NFC form (canonical composition)
        text = unicodedata.normalize("NFC", text)

        # Handle common Unicode issues
        replacements = {
            "\u200b": "",  # Zero-width space
            "\u200c": "",  # Zero-width non-joiner
            "\u200d": "",  # Zero-width joiner
            "\u2018": "'",  # Left single quotation mark
            "\u2019": "'",  # Right single quotation mark
            "\u201c": '"',  # Left double quotation mark
            "\u201d": '"',  # Right double quotation mark
            "\u2013": "-",  # En dash
            "\u2014": "-",  # Em dash
            "\u2026": "...",  # Horizontal ellipsis
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def remove_special_characters(self, text: str) -> str:
        """
        Remove special characters while preserving Hebrew, English, numbers, and basic punctuation.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        # Keep: Hebrew (0590-05FF), English (a-zA-Z), numbers, basic punctuation, whitespace
        pattern = r"[^\u0590-\u05FFa-zA-Z0-9\s.,!?;:()\-\'\"\n\r]"
        text = re.sub(pattern, "", text)

        return text

    def normalize_whitespace(self, text: str, preserve_paragraphs: bool = False) -> str:
        """
        Normalize whitespace in text.

        Args:
            text: Input text
            preserve_paragraphs: Whether to preserve paragraph breaks

        Returns:
            Text with normalized whitespace
        """
        if preserve_paragraphs:
            # Split into paragraphs
            paragraphs = re.split(r"\n\s*\n", text)

            # Clean each paragraph
            cleaned_paragraphs = []
            for para in paragraphs:
                # Replace multiple spaces with single space
                para = re.sub(r"[ \t]+", " ", para)
                # Remove leading/trailing whitespace
                para = para.strip()
                if para:
                    cleaned_paragraphs.append(para)

            # Join with double newline
            return "\n\n".join(cleaned_paragraphs)
        else:
            # Replace all whitespace (including newlines) with single space
            text = re.sub(r"\s+", " ", text)
            return text.strip()

    def truncate(self, text: str, max_length: int = 10000, ellipsis: str = "...") -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Input text
            max_length: Maximum length
            ellipsis: String to append if truncated

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        return text[: max_length - len(ellipsis)] + ellipsis

    def extract_excerpt(self, text: str, length: int = 200) -> str:
        """
        Extract a short excerpt from text.

        Args:
            text: Input text
            length: Desired excerpt length

        Returns:
            Excerpt
        """
        # Clean and truncate
        cleaned = self.clean_text(text, preserve_paragraphs=False)
        return self.truncate(cleaned, length)
