"""Make.com API client."""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional


class MakeClient:
    """Client for Make.com API and webhooks."""

    def __init__(self, config_path: str = "config/makecom.json"):
        """
        Initialize Make.com client.

        Args:
            config_path: Path to Make.com configuration file
        """
        self.logger = logging.getLogger(__name__)

        # Load configuration
        with open(config_path, "r") as f:
            self.config = json.load(f)

        # Get API key from environment
        self.api_key = os.getenv("MAKE_API_KEY", "")
        self.team_id = self.config.get("team_id")
        self.organization_id = self.config.get("organization_id")
        self.region = self.config.get("region", "us")

        # Base URL based on region
        if self.region == "eu":
            self.base_url = "https://eu1.make.com/api/v2"
        else:
            self.base_url = "https://us1.make.com/api/v2"

        # Scenarios configuration
        self.scenarios = {s["scenario_id"]: s for s in self.config.get("scenarios", [])}

        # Settings
        self.timeout = self.config.get("settings", {}).get("timeout", 30)
        self.retry_attempts = self.config.get("settings", {}).get("retry_attempts", 3)

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """
        List all scenarios.

        Returns:
            List of scenario dictionaries
        """
        try:
            if not self.api_key:
                self.logger.warning("Make.com API key not configured")
                return list(self.scenarios.values())

            headers = {"Authorization": f"Token {self.api_key}"}

            response = requests.get(
                f"{self.base_url}/scenarios",
                headers=headers,
                params={"teamId": self.team_id, "organizationId": self.organization_id},
                timeout=self.timeout,
            )

            response.raise_for_status()
            return response.json().get("scenarios", [])

        except requests.RequestException as e:
            self.logger.error(f"Error listing scenarios: {e}")
            return list(self.scenarios.values())
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return list(self.scenarios.values())

    def trigger_scenario(
        self, scenario_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger a scenario with data.

        Args:
            scenario_id: ID of scenario to trigger
            data: Data to send to scenario

        Returns:
            Response dictionary or None on error
        """
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            self.logger.error(f"Scenario not found: {scenario_id}")
            return None

        if not scenario.get("enabled", True):
            self.logger.info(f"Scenario {scenario_id} is disabled")
            return None

        webhook_url = scenario.get("webhook_url")
        if not webhook_url:
            self.logger.error(f"No webhook URL for scenario {scenario_id}")
            return None

        return self.send_webhook(webhook_url, data)

    def send_webhook(self, url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send data to a webhook URL.

        Args:
            url: Webhook URL
            payload: Data to send

        Returns:
            Response dictionary or None on error
        """
        for attempt in range(self.retry_attempts):
            try:
                self.logger.info(f"Sending webhook (attempt {attempt + 1}/{self.retry_attempts})")

                response = requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout,
                )

                response.raise_for_status()

                self.logger.info(f"Webhook sent successfully. Status: {response.status_code}")

                # Try to parse JSON response, but don't fail if not JSON
                try:
                    return response.json()
                except:
                    return {
                        "status": response.status_code,
                        "text": response.text,
                        "success": True,
                    }

            except requests.RequestException as e:
                self.logger.warning(f"Webhook attempt {attempt + 1} failed: {e}")
                if attempt == self.retry_attempts - 1:
                    self.logger.error(f"All webhook attempts failed: {e}")
                    return None

        return None

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a scenario execution.

        Args:
            execution_id: Execution ID

        Returns:
            Status dictionary or None
        """
        try:
            if not self.api_key:
                self.logger.warning("Make.com API key not configured")
                return None

            headers = {"Authorization": f"Token {self.api_key}"}

            response = requests.get(
                f"{self.base_url}/executions/{execution_id}",
                headers=headers,
                timeout=self.timeout,
            )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            self.logger.error(f"Error getting execution status: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None

    def get_scenario_for_content_type(self, content_type: str) -> Optional[Dict[str, Any]]:
        """
        Get appropriate scenario for content type.

        Args:
            content_type: Type of content (rss, email, web)

        Returns:
            Scenario dictionary or None
        """
        for scenario in self.scenarios.values():
            if not scenario.get("enabled", True):
                continue

            content_types = scenario.get("content_types", [])
            if content_type in content_types:
                return scenario

        # Return first enabled scenario as fallback
        for scenario in self.scenarios.values():
            if scenario.get("enabled", True):
                return scenario

        return None

    def send_batch(
        self, items: List[Dict[str, Any]], content_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Send multiple items to Make.com.

        Args:
            items: List of items to send
            content_type: Optional content type to determine scenario

        Returns:
            List of response dictionaries
        """
        results = []

        # Determine scenario
        if content_type:
            scenario = self.get_scenario_for_content_type(content_type)
            if not scenario:
                self.logger.error(f"No scenario found for content type: {content_type}")
                return results
            webhook_url = scenario.get("webhook_url")
        else:
            # Use first enabled scenario
            scenario = next(
                (s for s in self.scenarios.values() if s.get("enabled", True)), None
            )
            if not scenario:
                self.logger.error("No enabled scenarios found")
                return results
            webhook_url = scenario.get("webhook_url")

        # Send each item
        for i, item in enumerate(items, 1):
            self.logger.info(f"Sending item {i}/{len(items)} to Make.com")
            response = self.send_webhook(webhook_url, item)
            results.append(
                {
                    "item": item.get("title", "Unknown"),
                    "response": response,
                    "success": response is not None,
                }
            )

        return results

    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate Make.com configuration.

        Returns:
            Validation results
        """
        issues = []
        warnings = []

        # Check API key
        if not self.api_key:
            warnings.append("API key not configured (webhook-only mode)")

        # Check scenarios
        if not self.scenarios:
            issues.append("No scenarios configured")
        else:
            enabled_scenarios = [s for s in self.scenarios.values() if s.get("enabled", True)]
            if not enabled_scenarios:
                issues.append("No enabled scenarios")

            for scenario in self.scenarios.values():
                if not scenario.get("webhook_url"):
                    issues.append(f"Scenario {scenario.get('name')} has no webhook URL")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "scenario_count": len(self.scenarios),
            "enabled_scenario_count": len(
                [s for s in self.scenarios.values() if s.get("enabled", True)]
            ),
        }
