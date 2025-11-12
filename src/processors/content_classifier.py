"""Content classification and analysis."""

import re
import logging
from typing import Dict, Any, List
from collections import Counter


class ContentClassifier:
    """Classify and analyze content."""

    def __init__(self):
        """Initialize classifier."""
        self.logger = logging.getLogger(__name__)

    def classify(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify content and add classification metadata.

        Args:
            content: Content dictionary

        Returns:
            Content with added classification
        """
        try:
            classified = content.copy()

            # Detect language
            language = self.detect_language(content.get("body", ""), content.get("title", ""))
            classified["detected_language"] = language

            # Identify content type
            content_type = self.identify_content_type(content)
            classified["identified_type"] = content_type

            # Extract keywords
            keywords = self.extract_keywords(content.get("body", ""))
            classified["keywords"] = keywords

            # Assign priority
            priority = self.assign_priority(content)
            classified["assigned_priority"] = priority

            # Estimate reading time
            reading_time = self.estimate_reading_time(content.get("body", ""))
            classified["reading_time_minutes"] = reading_time

            return classified

        except Exception as e:
            self.logger.error(f"Error classifying content: {e}")
            return content

    def detect_language(self, body: str, title: str = "") -> str:
        """
        Detect content language.

        Args:
            body: Content body
            title: Content title

        Returns:
            Language code (en, he, mixed, unknown)
        """
        text = f"{title} {body}".lower()

        if not text.strip():
            return "unknown"

        # Count character types
        hebrew_chars = sum(1 for char in text if "\u0590" <= char <= "\u05ff")
        english_chars = sum(1 for char in text if "a" <= char <= "z")
        total_chars = hebrew_chars + english_chars

        if total_chars == 0:
            return "unknown"

        hebrew_ratio = hebrew_chars / total_chars
        english_ratio = english_chars / total_chars

        # Determine language based on ratios
        if hebrew_ratio > 0.3 and english_ratio > 0.3:
            return "mixed"
        elif hebrew_ratio > english_ratio:
            return "he"
        elif english_ratio > hebrew_ratio:
            return "en"
        else:
            return "unknown"

    def identify_content_type(self, content: Dict[str, Any]) -> str:
        """
        Identify the type of content.

        Args:
            content: Content dictionary

        Returns:
            Content type (article, email, post, news, other)
        """
        source_type = content.get("content_type", "").lower()

        # Direct mapping from source type
        if source_type == "email":
            return "email"
        elif source_type == "rss":
            # Analyze to determine if news or article
            body = content.get("body", "").lower()
            if any(word in body for word in ["breaking", "update", "reported", "announced"]):
                return "news"
            return "article"
        elif source_type == "web":
            return "article"
        else:
            return "other"

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text.

        Args:
            text: Input text
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of keywords
        """
        if not text:
            return []

        # Convert to lowercase
        text = text.lower()

        # Remove punctuation and split into words
        words = re.findall(r"\b\w+\b", text)

        # Filter out common stop words (basic list)
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "they",
            "them",
            "their",
        }

        # Filter and count
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]

        # Get most common
        word_counts = Counter(filtered_words)
        keywords = [word for word, count in word_counts.most_common(max_keywords)]

        return keywords

    def assign_priority(self, content: Dict[str, Any]) -> str:
        """
        Assign priority to content.

        Args:
            content: Content dictionary

        Returns:
            Priority level (high, medium, low)
        """
        # Start with source priority
        priority = content.get("priority", "medium").lower()

        # Adjust based on keywords
        body = content.get("body", "").lower()
        title = content.get("title", "").lower()

        high_priority_keywords = [
            "urgent",
            "important",
            "critical",
            "breaking",
            "alert",
            "emergency",
            "action required",
        ]

        low_priority_keywords = ["fyi", "newsletter", "digest", "summary", "archive"]

        # Check for high priority keywords
        if any(keyword in title or keyword in body for keyword in high_priority_keywords):
            return "high"

        # Check for low priority keywords
        if any(keyword in title or keyword in body for keyword in low_priority_keywords):
            return "low"

        return priority

    def estimate_reading_time(self, text: str, words_per_minute: int = 200) -> int:
        """
        Estimate reading time in minutes.

        Args:
            text: Text to estimate
            words_per_minute: Average reading speed

        Returns:
            Estimated reading time in minutes
        """
        if not text:
            return 0

        # Count words (approximate)
        word_count = len(re.findall(r"\b\w+\b", text))

        # Calculate minutes
        minutes = max(1, round(word_count / words_per_minute))

        return minutes
