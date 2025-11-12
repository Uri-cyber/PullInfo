"""Base extractor class that all extractors inherit from."""

import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any


class BaseExtractor(ABC):
    """Base class for all content extractors."""

    def __init__(self, source_config: Dict[str, Any], cache_manager=None):
        """
        Initialize the extractor.

        Args:
            source_config: Configuration dictionary for this source
            cache_manager: Optional cache manager instance
        """
        self.source_id = source_config.get("source_id")
        self.source_type = source_config.get("type")
        self.url = source_config.get("url")
        self.enabled = source_config.get("enabled", True)
        self.priority = source_config.get("priority", "medium")
        self.config = source_config
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def fetch_content(self) -> List[Dict[str, Any]]:
        """
        Fetch content from the source.

        Returns:
            List of raw content items
        """
        pass

    @abstractmethod
    def parse_content(self, raw_content: Any) -> Dict[str, Any]:
        """
        Parse raw content into standardized format.

        Args:
            raw_content: Raw content from the source

        Returns:
            Parsed content dictionary
        """
        pass

    def validate_content(self, content: Dict[str, Any]) -> bool:
        """
        Validate that content has all required fields.

        Args:
            content: Content dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["source_id", "content_type", "title", "body", "timestamp"]

        for field in required_fields:
            if field not in content or not content[field]:
                self.logger.warning(f"Missing required field: {field}")
                return False

        return True

    def cache_result(self, content: Dict[str, Any]) -> bool:
        """
        Cache the content result.

        Args:
            content: Content to cache

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.cache_manager:
            return False

        try:
            content_hash = self.generate_content_hash(content)

            # Check if already cached
            if self.cache_manager.is_cached(content_hash):
                self.logger.info(f"Content already cached: {content_hash}")
                return False

            # Store in cache
            self.cache_manager.store(content_hash, content)
            return True

        except Exception as e:
            self.logger.error(f"Error caching content: {e}")
            return False

    def generate_content_hash(self, content: Dict[str, Any]) -> str:
        """
        Generate a unique hash for content.

        Args:
            content: Content dictionary

        Returns:
            SHA256 hash string
        """
        # Create hash from title and body
        hash_content = f"{content.get('title', '')}|{content.get('body', '')}"
        return hashlib.sha256(hash_content.encode()).hexdigest()

    def standardize_content(
        self,
        title: str,
        body: str,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create standardized content format.

        Args:
            title: Content title
            body: Content body
            url: Optional URL
            metadata: Optional metadata dictionary
            language: Optional language code

        Returns:
            Standardized content dictionary
        """
        return {
            "source_id": self.source_id,
            "content_type": self.source_type,
            "title": title,
            "body": body,
            "url": url or self.url,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "language": language,
            "priority": self.priority,
        }

    def extract(self) -> List[Dict[str, Any]]:
        """
        Main extraction method that orchestrates the process.

        Returns:
            List of standardized, validated content items
        """
        if not self.enabled:
            self.logger.info(f"Extractor {self.source_id} is disabled")
            return []

        try:
            self.logger.info(f"Starting extraction for {self.source_id}")

            # Fetch raw content
            raw_items = self.fetch_content()
            self.logger.info(f"Fetched {len(raw_items)} items from {self.source_id}")

            # Parse and validate each item
            valid_items = []
            for raw_item in raw_items:
                try:
                    parsed = self.parse_content(raw_item)

                    if self.validate_content(parsed):
                        # Check cache and add if new
                        if self.cache_result(parsed):
                            valid_items.append(parsed)
                        else:
                            self.logger.debug(f"Item already processed: {parsed.get('title')}")
                    else:
                        self.logger.warning(f"Invalid content from {self.source_id}")

                except Exception as e:
                    self.logger.error(f"Error parsing item: {e}")
                    continue

            self.logger.info(f"Extracted {len(valid_items)} new valid items from {self.source_id}")
            return valid_items

        except Exception as e:
            self.logger.error(f"Error extracting from {self.source_id}: {e}")
            return []
