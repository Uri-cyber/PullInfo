"""Tests for database manager."""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from database import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db = DatabaseManager(db_path=self.temp_db.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        # Close and remove temporary database
        self.temp_db.close()
        os.unlink(self.temp_db.name)

    def test_initialization(self):
        """Test database initialization."""
        # Database should be initialized
        assert os.path.exists(self.temp_db.name)

    def test_store_and_retrieve(self):
        """Test storing and retrieving content."""
        content = {
            "source_id": "test",
            "title": "Test Title",
            "body": "Test Body",
            "url": "https://example.com",
            "timestamp": "2025-01-01T00:00:00"
        }

        # Generate hash
        content_hash = "test_hash_123"

        # Store content
        content_id = self.db.store(content_hash, content)
        assert content_id > 0

        # Check if cached
        assert self.db.is_cached(content_hash) is True

        # Retrieve content
        retrieved = self.db.get_cached_content(content_hash)
        assert retrieved is not None
        assert retrieved["title"] == "Test Title"

    def test_store_summary(self):
        """Test storing summaries."""
        content_hash = "test_hash_456"

        # First store content
        content = {
            "source_id": "test",
            "title": "Test",
            "body": "Content"
        }
        self.db.store(content_hash, content)

        # Store summary
        summary = {
            "summary": "This is a test summary",
            "style": "quick_summary",
            "language": "en",
            "tokens": {"total": 100},
            "cost_usd": 0.001
        }

        summary_id = self.db.store_summary(content_hash, summary)
        assert summary_id > 0

        # Retrieve summary
        retrieved = self.db.get_summary_for_content(content_hash)
        assert retrieved is not None
        assert retrieved["summary"] == "This is a test summary"

    def test_log_api_call(self):
        """Test API call logging."""
        log_id = self.db.log_api_call(
            endpoint="claude",
            request_data={"prompt": "test"},
            response_data={"result": "success"},
            tokens_input=100,
            tokens_output=50,
            cost=0.001
        )

        assert log_id > 0

    def test_get_stats(self):
        """Test statistics retrieval."""
        stats = self.db.get_stats(days=30)

        assert "content_processed" in stats
        assert "summaries_generated" in stats
        assert "total_cost" in stats
        assert isinstance(stats["content_processed"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
