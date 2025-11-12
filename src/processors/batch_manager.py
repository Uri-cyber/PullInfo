"""Batch management for content processing."""

import logging
from typing import Dict, List, Any
from collections import defaultdict


class BatchManager:
    """Manage batches of content for processing."""

    def __init__(self, max_tokens: int = 150000):
        """
        Initialize batch manager.

        Args:
            max_tokens: Maximum tokens per batch (staying under 200k limit)
        """
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)

    def create_batches(
        self, content_list: List[Dict[str, Any]], group_by: str = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Create batches from content list.

        Args:
            content_list: List of content items
            group_by: Optional field to group by (e.g., 'language', 'content_type')

        Returns:
            List of batches (each batch is a list of content items)
        """
        if not content_list:
            return []

        if group_by:
            # Group by specified field first
            groups = self._group_content(content_list, group_by)

            # Create batches for each group
            all_batches = []
            for group_key, group_items in groups.items():
                self.logger.info(f"Creating batches for {group_by}={group_key}")
                batches = self._create_token_based_batches(group_items)
                all_batches.extend(batches)

            return all_batches
        else:
            # Create batches without grouping
            return self._create_token_based_batches(content_list)

    def _group_content(
        self, content_list: List[Dict[str, Any]], group_by: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group content by a field.

        Args:
            content_list: List of content items
            group_by: Field to group by

        Returns:
            Dictionary of grouped content
        """
        groups = defaultdict(list)

        for item in content_list:
            group_key = item.get(group_by, "unknown")
            groups[group_key].append(item)

        return dict(groups)

    def _create_token_based_batches(
        self, content_list: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Create batches based on token limits.

        Args:
            content_list: List of content items

        Returns:
            List of batches
        """
        batches = []
        current_batch = []
        current_tokens = 0

        for item in content_list:
            # Estimate tokens for this item (rough estimate: 1 token ≈ 4 characters)
            item_tokens = self._estimate_tokens(item)

            # Check if adding this item would exceed limit
            if current_tokens + item_tokens > self.max_tokens and current_batch:
                # Save current batch and start new one
                batches.append(current_batch)
                current_batch = [item]
                current_tokens = item_tokens
            else:
                # Add to current batch
                current_batch.append(item)
                current_tokens += item_tokens

        # Add final batch if not empty
        if current_batch:
            batches.append(current_batch)

        self.logger.info(
            f"Created {len(batches)} batches from {len(content_list)} items"
        )

        return batches

    def _estimate_tokens(self, content: Dict[str, Any]) -> int:
        """
        Estimate token count for content.

        Args:
            content: Content dictionary

        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters
        # Count title and body characters
        title = content.get("title", "")
        body = content.get("body", "")

        total_chars = len(title) + len(body)
        estimated_tokens = total_chars // 4

        # Add some overhead for JSON structure
        return estimated_tokens + 100

    def optimize_batch_order(
        self, batches: List[List[Dict[str, Any]]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Optimize batch processing order based on priority.

        Args:
            batches: List of batches

        Returns:
            Reordered list of batches
        """
        priority_order = {"high": 0, "medium": 1, "low": 2}

        # Sort batches by highest priority item in each batch
        def batch_priority(batch):
            priorities = [
                priority_order.get(item.get("priority", "medium"), 1) for item in batch
            ]
            return min(priorities) if priorities else 1

        sorted_batches = sorted(batches, key=batch_priority)

        return sorted_batches

    def get_batch_stats(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics for a batch.

        Args:
            batch: List of content items

        Returns:
            Statistics dictionary
        """
        if not batch:
            return {"count": 0, "total_tokens": 0}

        total_tokens = sum(self._estimate_tokens(item) for item in batch)

        # Count by language
        languages = defaultdict(int)
        for item in batch:
            lang = item.get("detected_language") or item.get("language", "unknown")
            languages[lang] += 1

        # Count by priority
        priorities = defaultdict(int)
        for item in batch:
            priority = item.get("priority", "medium")
            priorities[priority] += 1

        return {
            "count": len(batch),
            "total_tokens": total_tokens,
            "languages": dict(languages),
            "priorities": dict(priorities),
        }
