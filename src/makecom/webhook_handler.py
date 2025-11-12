"""Webhook handler for Make.com integration."""

import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime


class WebhookHandler:
    """Handle webhook operations for Make.com."""

    def __init__(self):
        """Initialize webhook handler."""
        self.logger = logging.getLogger(__name__)

    def generate_webhook_id(self, content: Dict[str, Any]) -> str:
        """
        Generate unique webhook ID for content.

        Args:
            content: Content dictionary

        Returns:
            Unique webhook ID
        """
        # Create hash from content
        hash_input = f"{content.get('source_id')}|{content.get('title')}|{content.get('timestamp')}"
        webhook_id = hashlib.md5(hash_input.encode()).hexdigest()[:16]
        return webhook_id

    def format_payload(
        self,
        content: Dict[str, Any],
        summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format content and summary for Make.com webhook.

        Args:
            content: Original content dictionary
            summary: Optional summary dictionary

        Returns:
            Formatted payload
        """
        payload = {
            "webhook_id": self.generate_webhook_id(content),
            "timestamp": datetime.utcnow().isoformat(),
            "content": {
                "source_id": content.get("source_id"),
                "title": content.get("title"),
                "url": content.get("url"),
                "content_type": content.get("content_type"),
                "language": content.get("language") or content.get("detected_language"),
                "priority": content.get("priority") or content.get("assigned_priority", "medium"),
                "original_timestamp": content.get("timestamp"),
            },
            "body_excerpt": self._create_excerpt(content.get("body", ""), max_length=200),
        }

        # Add summary if available
        if summary and "summary" in summary:
            payload["summary"] = {
                "text": summary.get("summary"),
                "style": summary.get("style"),
                "word_count": len(summary.get("summary", "").split()),
                "tokens_used": summary.get("tokens", {}).get("total", 0),
                "cost_usd": summary.get("cost_usd", 0),
            }

        # Add metadata
        if "metadata" in content:
            payload["metadata"] = content["metadata"]

        # Add classification if available
        if "keywords" in content:
            payload["keywords"] = content["keywords"]

        if "reading_time_minutes" in content:
            payload["reading_time_minutes"] = content["reading_time_minutes"]

        return payload

    def validate_response(self, response: Any) -> bool:
        """
        Validate webhook response.

        Args:
            response: Response from webhook

        Returns:
            True if valid, False otherwise
        """
        if response is None:
            self.logger.warning("Webhook response is None")
            return False

        if isinstance(response, dict):
            # Check for success indicators
            if response.get("success") or response.get("status") == 200:
                return True

            # Check for error indicators
            if "error" in response:
                self.logger.error(f"Webhook error: {response['error']}")
                return False

        return True

    def handle_error(self, content: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """
        Handle webhook error.

        Args:
            content: Content that failed
            error: Exception that occurred

        Returns:
            Error information dictionary
        """
        self.logger.error(f"Webhook error for {content.get('title')}: {error}")

        return {
            "webhook_id": self.generate_webhook_id(content),
            "content_id": content.get("source_id"),
            "title": content.get("title"),
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "retry_possible": True,
        }

    def create_batch_payload(
        self,
        items: list[Dict[str, Any]],
        batch_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create batch payload for multiple items.

        Args:
            items: List of formatted payloads
            batch_metadata: Optional batch metadata

        Returns:
            Batch payload
        """
        return {
            "batch_id": hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:16],
            "timestamp": datetime.utcnow().isoformat(),
            "item_count": len(items),
            "items": items,
            "metadata": batch_metadata or {},
        }

    def _create_excerpt(self, text: str, max_length: int = 200) -> str:
        """
        Create excerpt from text.

        Args:
            text: Full text
            max_length: Maximum length

        Returns:
            Excerpt
        """
        if not text:
            return ""

        # Clean whitespace
        text = " ".join(text.split())

        if len(text) <= max_length:
            return text

        # Truncate at word boundary
        excerpt = text[:max_length]
        last_space = excerpt.rfind(" ")
        if last_space > 0:
            excerpt = excerpt[:last_space]

        return excerpt + "..."
