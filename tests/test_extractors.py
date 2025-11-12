"""Tests for content extractors."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from extractors.base_extractor import BaseExtractor


class MockExtractor(BaseExtractor):
    """Mock extractor for testing."""

    def fetch_content(self):
        """Mock fetch content."""
        return [{"title": "Test", "body": "Content"}]

    def parse_content(self, raw_content):
        """Mock parse content."""
        return self.standardize_content(
            title=raw_content.get("title", ""),
            body=raw_content.get("body", ""),
        )


class TestBaseExtractor:
    """Test BaseExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "source_id": "test_source",
            "type": "test",
            "url": "https://example.com",
            "enabled": True,
            "priority": "high"
        }
        self.extractor = MockExtractor(self.config)

    def test_initialization(self):
        """Test extractor initialization."""
        assert self.extractor.source_id == "test_source"
        assert self.extractor.source_type == "test"
        assert self.extractor.url == "https://example.com"
        assert self.extractor.enabled is True
        assert self.extractor.priority == "high"

    def test_standardize_content(self):
        """Test content standardization."""
        content = self.extractor.standardize_content(
            title="Test Title",
            body="Test Body",
            url="https://example.com",
        )

        assert content["title"] == "Test Title"
        assert content["body"] == "Test Body"
        assert content["url"] == "https://example.com"
        assert content["source_id"] == "test_source"
        assert content["content_type"] == "test"
        assert "timestamp" in content

    def test_generate_content_hash(self):
        """Test content hash generation."""
        content1 = {"title": "Test", "body": "Content"}
        content2 = {"title": "Test", "body": "Content"}
        content3 = {"title": "Different", "body": "Content"}

        hash1 = self.extractor.generate_content_hash(content1)
        hash2 = self.extractor.generate_content_hash(content2)
        hash3 = self.extractor.generate_content_hash(content3)

        # Same content should produce same hash
        assert hash1 == hash2

        # Different content should produce different hash
        assert hash1 != hash3

    def test_validate_content(self):
        """Test content validation."""
        valid_content = {
            "source_id": "test",
            "content_type": "test",
            "title": "Test",
            "body": "Content",
            "timestamp": "2025-01-01T00:00:00"
        }

        invalid_content = {
            "title": "Test"
        }

        assert self.extractor.validate_content(valid_content) is True
        assert self.extractor.validate_content(invalid_content) is False

    def test_extract(self):
        """Test extraction process."""
        items = self.extractor.extract()
        assert isinstance(items, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
