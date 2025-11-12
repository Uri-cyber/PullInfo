"""RSS/Atom feed extractor."""

import feedparser
import requests
from typing import Dict, List, Any
from datetime import datetime
from .base_extractor import BaseExtractor


class RSSExtractor(BaseExtractor):
    """Extractor for RSS and Atom feeds."""

    def __init__(self, source_config: Dict[str, Any], cache_manager=None):
        """Initialize RSS extractor."""
        super().__init__(source_config, cache_manager)
        self.timeout = source_config.get("timeout", 30)

    def fetch_content(self) -> List[Dict[str, Any]]:
        """
        Fetch and parse RSS/Atom feed.

        Returns:
            List of feed entries
        """
        try:
            # Fetch the feed
            response = requests.get(self.url, timeout=self.timeout)
            response.raise_for_status()

            # Parse with feedparser
            feed = feedparser.parse(response.content)

            if feed.bozo:
                self.logger.warning(f"Feed parsing warning for {self.url}: {feed.bozo_exception}")

            return feed.entries

        except requests.RequestException as e:
            self.logger.error(f"Error fetching RSS feed {self.url}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error parsing RSS feed: {e}")
            return []

    def parse_content(self, raw_content: Any) -> Dict[str, Any]:
        """
        Parse RSS entry into standardized format.

        Args:
            raw_content: feedparser entry object

        Returns:
            Standardized content dictionary
        """
        # Extract title
        title = raw_content.get("title", "No Title")

        # Extract body (try multiple fields)
        body = (
            raw_content.get("content", [{}])[0].get("value")
            or raw_content.get("summary")
            or raw_content.get("description")
            or ""
        )

        # Extract URL
        url = raw_content.get("link", self.url)

        # Extract publish date
        published = raw_content.get("published_parsed") or raw_content.get("updated_parsed")
        if published:
            timestamp = datetime(*published[:6]).isoformat()
        else:
            timestamp = datetime.utcnow().isoformat()

        # Extract metadata
        metadata = {
            "author": raw_content.get("author", "Unknown"),
            "tags": [tag.term for tag in raw_content.get("tags", [])],
            "feed_title": raw_content.get("feed", {}).get("title", ""),
            "published": raw_content.get("published", ""),
        }

        # Detect language (basic)
        language = self._detect_language(title, body)

        return self.standardize_content(
            title=title,
            body=body,
            url=url,
            metadata=metadata,
            language=language,
        )

    def _detect_language(self, title: str, body: str) -> str:
        """
        Simple language detection.

        Args:
            title: Content title
            body: Content body

        Returns:
            Language code (en, he, or mixed)
        """
        text = f"{title} {body}".lower()

        # Check for Hebrew characters
        has_hebrew = any("\u0590" <= char <= "\u05ff" for char in text)

        # Check for English characters
        has_english = any("a" <= char <= "z" for char in text)

        if has_hebrew and has_english:
            return "mixed"
        elif has_hebrew:
            return "he"
        elif has_english:
            return "en"
        else:
            return "unknown"
