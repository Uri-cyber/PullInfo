"""Claude API client for content summarization."""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from datetime import datetime


class ClaudeClient:
    """Client for interacting with Claude API."""

    def __init__(self, config_path: str = "config/claude.json"):
        """
        Initialize Claude client.

        Args:
            config_path: Path to Claude configuration file
        """
        self.logger = logging.getLogger(__name__)

        # Load configuration
        with open(config_path, "r") as f:
            self.config = json.load(f)

        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        # Initialize Anthropic client
        self.client = Anthropic(api_key=api_key)

        # Load settings
        self.model = self.config.get("model", "claude-sonnet-4-20250514")
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.temperature = self.config.get("temperature", 0.7)
        self.prompt_templates = self.config.get("prompt_templates", {})
        self.default_template = self.config.get("default_prompt_template", "quick_summary")

        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.cost_limits = self.config.get("cost_limits", {})

        # Pricing (approximate for Sonnet 4)
        self.input_cost_per_million = 3.0  # $3 per million input tokens
        self.output_cost_per_million = 15.0  # $15 per million output tokens

    def generate_summary(
        self,
        content: Dict[str, Any],
        style: str = None,
        custom_prompt: str = None,
    ) -> Dict[str, Any]:
        """
        Generate summary for content.

        Args:
            content: Content dictionary with title and body
            style: Template style to use (quick_summary, detailed_analysis, etc.)
            custom_prompt: Optional custom prompt (overrides template)

        Returns:
            Dictionary with summary and metadata
        """
        try:
            # Get template
            template_name = style or self.default_template
            template = self.prompt_templates.get(template_name, self.prompt_templates["quick_summary"])

            # Build prompt
            if custom_prompt:
                user_prompt = custom_prompt.format(
                    title=content.get("title", ""),
                    content=content.get("body", ""),
                )
            else:
                user_prompt = template["user"].format(content=content.get("body", ""))

            system_prompt = template.get("system", "You are a helpful assistant.")
            max_tokens = template.get("max_tokens", self.max_tokens)

            # Make API call
            self.logger.info(f"Generating {template_name} summary for: {content.get('title', 'Untitled')}")

            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract response
            summary_text = message.content[0].text

            # Track usage
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

            # Calculate cost
            cost = self._calculate_cost(input_tokens, output_tokens)

            self.logger.info(
                f"Summary generated. Tokens: {input_tokens} in, {output_tokens} out. Cost: ${cost:.4f}"
            )

            return {
                "summary": summary_text,
                "style": template_name,
                "content_id": content.get("source_id"),
                "title": content.get("title"),
                "url": content.get("url"),
                "timestamp": datetime.utcnow().isoformat(),
                "tokens": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens,
                },
                "cost_usd": cost,
                "model": self.model,
            }

        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return {
                "error": str(e),
                "content_id": content.get("source_id"),
                "title": content.get("title"),
            }

    def batch_process(
        self,
        content_list: List[Dict[str, Any]],
        style: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple content items.

        Args:
            content_list: List of content dictionaries
            style: Template style to use

        Returns:
            List of summary dictionaries
        """
        summaries = []

        for i, content in enumerate(content_list, 1):
            self.logger.info(f"Processing item {i}/{len(content_list)}")

            # Check cost limits before processing
            if not self._check_cost_limit():
                self.logger.warning("Cost limit reached, stopping batch processing")
                break

            summary = self.generate_summary(content, style)
            summaries.append(summary)

        return summaries

    def estimate_cost(self, content: Dict[str, Any], style: str = None) -> Dict[str, Any]:
        """
        Estimate cost for processing content.

        Args:
            content: Content dictionary
            style: Template style

        Returns:
            Dictionary with cost estimates
        """
        # Rough token estimation (1 token ≈ 4 characters)
        body = content.get("body", "")
        estimated_input_tokens = len(body) // 4 + 200  # +200 for prompt overhead

        # Get expected output tokens from template
        template_name = style or self.default_template
        template = self.prompt_templates.get(template_name, {})
        estimated_output_tokens = template.get("max_tokens", 500)

        # Calculate cost
        cost = self._calculate_cost(estimated_input_tokens, estimated_output_tokens)

        return {
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "estimated_cost_usd": cost,
        }

    def track_usage(self) -> Dict[str, Any]:
        """
        Get current usage statistics.

        Returns:
            Dictionary with usage stats
        """
        total_cost = self._calculate_cost(self.total_input_tokens, self.total_output_tokens)

        # Check against limits
        daily_limit = self.cost_limits.get("daily_limit_usd", 5.0)
        monthly_limit = self.cost_limits.get("monthly_limit_usd", 100.0)

        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": total_cost,
            "cost_limits": {
                "daily_limit": daily_limit,
                "monthly_limit": monthly_limit,
                "daily_remaining": max(0, daily_limit - total_cost),
                "alert_threshold": self.cost_limits.get("alert_threshold", 0.8),
            },
        }

    def reset_usage(self):
        """Reset usage counters."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.logger.info("Usage counters reset")

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million
        return input_cost + output_cost

    def _check_cost_limit(self) -> bool:
        """
        Check if within cost limits.

        Returns:
            True if within limits, False otherwise
        """
        usage = self.track_usage()
        total_cost = usage["total_cost_usd"]
        daily_limit = usage["cost_limits"]["daily_limit"]

        if total_cost >= daily_limit:
            self.logger.warning(f"Daily cost limit reached: ${total_cost:.2f} >= ${daily_limit:.2f}")
            return False

        # Check alert threshold
        threshold = usage["cost_limits"]["alert_threshold"]
        if total_cost >= daily_limit * threshold:
            self.logger.warning(
                f"Approaching cost limit: ${total_cost:.2f} "
                f"({(total_cost/daily_limit)*100:.1f}% of daily limit)"
            )

        return True

    def get_available_templates(self) -> List[str]:
        """
        Get list of available prompt templates.

        Returns:
            List of template names
        """
        return list(self.prompt_templates.keys())

    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific template.

        Args:
            template_name: Name of template

        Returns:
            Template configuration or None
        """
        return self.prompt_templates.get(template_name)
