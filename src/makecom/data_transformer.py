"""Data transformer for Make.com format conversion."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime


class DataTransformer:
    """Transform data for Make.com consumption."""

    def __init__(self):
        """Initialize data transformer."""
        self.logger = logging.getLogger(__name__)

    def transform_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform content to Make.com format.

        Args:
            content: Content dictionary

        Returns:
            Transformed content
        """
        try:
            transformed = {
                # Standard Make.com fields
                "Name": content.get("title", "Untitled"),
                "Description": self._truncate_text(content.get("body", ""), 1000),
                "URL": content.get("url", ""),
                "Date": content.get("timestamp", datetime.utcnow().isoformat()),
                # Custom fields
                "SourceID": content.get("source_id", "unknown"),
                "ContentType": content.get("content_type", "unknown"),
                "Language": content.get("language") or content.get("detected_language", "unknown"),
                "Priority": content.get("priority") or content.get("assigned_priority", "medium"),
            }

            # Add optional fields
            if "keywords" in content:
                transformed["Keywords"] = ", ".join(content["keywords"][:5])

            if "reading_time_minutes" in content:
                transformed["ReadingTime"] = f"{content['reading_time_minutes']} min"

            if "metadata" in content and isinstance(content["metadata"], dict):
                # Add metadata as additional fields
                metadata = content["metadata"]
                if "author" in metadata:
                    transformed["Author"] = metadata["author"]

            return transformed

        except Exception as e:
            self.logger.error(f"Error transforming content: {e}")
            return {}

    def transform_summary(
        self,
        summary: Dict[str, Any],
        original_content: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transform summary to Make.com format.

        Args:
            summary: Summary dictionary
            original_content: Optional original content

        Returns:
            Transformed summary
        """
        try:
            transformed = {
                "Name": summary.get("title", "Summary"),
                "Summary": summary.get("summary", ""),
                "URL": summary.get("url", ""),
                "Date": summary.get("timestamp", datetime.utcnow().isoformat()),
                "SummaryStyle": summary.get("style", "quick_summary"),
                "Model": summary.get("model", "claude"),
                "TokensUsed": summary.get("tokens", {}).get("total", 0),
                "CostUSD": round(summary.get("cost_usd", 0), 4),
            }

            # Add original content info if available
            if original_content:
                transformed["OriginalTitle"] = original_content.get("title", "")
                transformed["SourceID"] = original_content.get("source_id", "")
                transformed["ContentType"] = original_content.get("content_type", "")

            return transformed

        except Exception as e:
            self.logger.error(f"Error transforming summary: {e}")
            return {}

    def transform_combined(
        self,
        content: Dict[str, Any],
        summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transform content and summary into combined format.

        Args:
            content: Content dictionary
            summary: Optional summary dictionary

        Returns:
            Combined transformed data
        """
        try:
            # Start with content transformation
            transformed = self.transform_content(content)

            # Add summary if available
            if summary and "summary" in summary:
                transformed["Summary"] = summary.get("summary", "")
                transformed["SummaryStyle"] = summary.get("style", "")
                transformed["AIModel"] = summary.get("model", "")
                transformed["ProcessingCost"] = round(summary.get("cost_usd", 0), 4)
                transformed["TokensUsed"] = summary.get("tokens", {}).get("total", 0)

            return transformed

        except Exception as e:
            self.logger.error(f"Error transforming combined data: {e}")
            return {}

    def validate_transformed(self, data: Dict[str, Any]) -> bool:
        """
        Validate transformed data.

        Args:
            data: Transformed data dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["Name", "Date"]

        for field in required_fields:
            if field not in data or not data[field]:
                self.logger.warning(f"Missing required field: {field}")
                return False

        return True

    def transform_batch(
        self,
        content_list: List[Dict[str, Any]],
        summaries: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Transform batch of content and summaries.

        Args:
            content_list: List of content dictionaries
            summaries: Optional list of summary dictionaries

        Returns:
            List of transformed items
        """
        transformed_items = []

        for i, content in enumerate(content_list):
            # Get corresponding summary if available
            summary = None
            if summaries and i < len(summaries):
                summary = summaries[i]

            # Transform
            transformed = self.transform_combined(content, summary)

            # Validate
            if self.validate_transformed(transformed):
                transformed_items.append(transformed)
            else:
                self.logger.warning(f"Invalid transformed data for: {content.get('title')}")

        return transformed_items

    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Input text
            max_length: Maximum length

        Returns:
            Truncated text
        """
        if not text:
            return ""

        # Clean whitespace
        text = " ".join(text.split())

        if len(text) <= max_length:
            return text

        # Truncate at word boundary
        truncated = text[: max_length - 3]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]

        return truncated + "..."
