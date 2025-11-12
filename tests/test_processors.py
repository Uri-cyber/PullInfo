"""Tests for content processors."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from processors.content_cleaner import ContentCleaner
from processors.content_classifier import ContentClassifier
from processors.batch_manager import BatchManager


class TestContentCleaner:
    """Test ContentCleaner class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cleaner = ContentCleaner()

    def test_remove_html(self):
        """Test HTML removal."""
        text = "<p>Hello <b>world</b></p>"
        cleaned = self.cleaner.remove_html(text)
        assert cleaned == "Hello world"

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = "Hello    world\n\n\ntest"
        cleaned = self.cleaner.normalize_whitespace(text, preserve_paragraphs=False)
        assert cleaned == "Hello world test"

    def test_clean_text(self):
        """Test full text cleaning."""
        text = "<p>Hello   world!</p>\n\nTest content."
        cleaned = self.cleaner.clean_text(text, preserve_paragraphs=True)
        assert "Hello world!" in cleaned
        assert "<p>" not in cleaned


class TestContentClassifier:
    """Test ContentClassifier class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = ContentClassifier()

    def test_detect_english(self):
        """Test English language detection."""
        text = "This is an English text with many words."
        language = self.classifier.detect_language(text, "")
        assert language == "en"

    def test_detect_hebrew(self):
        """Test Hebrew language detection."""
        text = "שלום עולם זה טקסט בעברית"
        language = self.classifier.detect_language(text, "")
        assert language == "he"

    def test_extract_keywords(self):
        """Test keyword extraction."""
        text = "Python programming language is great for machine learning and data science."
        keywords = self.classifier.extract_keywords(text, max_keywords=5)
        assert len(keywords) <= 5
        assert isinstance(keywords, list)

    def test_estimate_reading_time(self):
        """Test reading time estimation."""
        text = " ".join(["word"] * 200)  # 200 words
        time_minutes = self.classifier.estimate_reading_time(text, words_per_minute=200)
        assert time_minutes == 1


class TestBatchManager:
    """Test BatchManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.batch_manager = BatchManager(max_tokens=1000)

    def test_create_batches(self):
        """Test batch creation."""
        content_list = [
            {"title": f"Title {i}", "body": "Short content " * 10}
            for i in range(5)
        ]

        batches = self.batch_manager.create_batches(content_list)
        assert len(batches) > 0
        assert isinstance(batches, list)

    def test_estimate_tokens(self):
        """Test token estimation."""
        content = {
            "title": "Test Title",
            "body": "This is a test body with some content."
        }

        tokens = self.batch_manager._estimate_tokens(content)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_group_content(self):
        """Test content grouping."""
        content_list = [
            {"title": "Item 1", "language": "en"},
            {"title": "Item 2", "language": "he"},
            {"title": "Item 3", "language": "en"},
        ]

        groups = self.batch_manager._group_content(content_list, "language")
        assert "en" in groups
        assert "he" in groups
        assert len(groups["en"]) == 2
        assert len(groups["he"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
