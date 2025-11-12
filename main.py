#!/usr/bin/env python3
"""Content Monitor - Main entry point and CLI interface."""

import os
import sys
import argparse
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from logger import setup_logging, ActivityLogger
from database import DatabaseManager
from claude_client import ClaudeClient
from extractors import RSSExtractor, WebExtractor, EmailExtractor
from processors import ContentCleaner, ContentClassifier, BatchManager
from makecom import MakeClient, WebhookHandler, DataTransformer
from scheduler import ContentScheduler


class ContentMonitor:
    """Main application class."""

    def __init__(self):
        """Initialize content monitor."""
        # Setup logging
        self.logger = setup_logging()
        self.activity_logger = ActivityLogger(self.logger)

        # Initialize components
        self.db = DatabaseManager()
        self.claude_client = ClaudeClient()
        self.make_client = MakeClient()
        self.webhook_handler = WebhookHandler()
        self.data_transformer = DataTransformer()

        # Processors
        self.cleaner = ContentCleaner()
        self.classifier = ContentClassifier()
        self.batch_manager = BatchManager()

        # Load sources
        with open("config/sources.json", "r") as f:
            self.config = json.load(f)
            self.sources = self.config.get("sources", [])

        self.logger.info("Content Monitor initialized")

    def extract_from_source(self, source_id: str) -> List[Dict[str, Any]]:
        """
        Extract content from a specific source.

        Args:
            source_id: Source ID

        Returns:
            List of extracted content items
        """
        # Find source config
        source = next((s for s in self.sources if s.get("source_id") == source_id), None)

        if not source:
            self.logger.error(f"Source not found: {source_id}")
            return []

        if not source.get("enabled", True):
            self.logger.info(f"Source {source_id} is disabled")
            return []

        start_time = time.time()

        try:
            # Create appropriate extractor
            source_type = source.get("type")

            if source_type == "rss":
                extractor = RSSExtractor(source, self.db)
            elif source_type == "web":
                extractor = WebExtractor(source, self.db)
            elif source_type == "email":
                extractor = EmailExtractor(source, self.db)
            else:
                self.logger.error(f"Unknown source type: {source_type}")
                return []

            # Extract content
            items = extractor.extract()

            duration = time.time() - start_time
            self.activity_logger.log_extraction(source_id, len(items), duration, success=True)

            return items

        except Exception as e:
            duration = time.time() - start_time
            self.activity_logger.log_extraction(source_id, 0, duration, success=False, error=str(e))
            return []

    def process_content(
        self, content_list: List[Dict[str, Any]], summarize: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process content through cleaning, classification, and summarization.

        Args:
            content_list: List of content items
            summarize: Whether to generate summaries

        Returns:
            List of processed items with summaries
        """
        if not content_list:
            return []

        start_time = time.time()
        total_tokens = 0
        total_cost = 0

        try:
            # Clean content
            cleaned_items = [self.cleaner.clean(item) for item in content_list]

            # Classify content
            classified_items = [self.classifier.classify(item) for item in cleaned_items]

            # Generate summaries if requested
            summaries = []
            if summarize:
                summaries = self.claude_client.batch_process(classified_items)

                # Track usage
                for summary in summaries:
                    if "tokens" in summary:
                        total_tokens += summary["tokens"].get("total", 0)
                    if "cost_usd" in summary:
                        total_cost += summary["cost_usd"]

                    # Store in database
                    content_hash = self.db.generate_content_hash(classified_items[summaries.index(summary)])
                    self.db.store_summary(content_hash, summary)

            duration = time.time() - start_time
            self.activity_logger.log_processing(
                len(content_list), duration, total_tokens, total_cost, success=True
            )

            return summaries

        except Exception as e:
            duration = time.time() - start_time
            self.activity_logger.log_processing(
                len(content_list), duration, total_tokens, total_cost, success=False, error=str(e)
            )
            return []

    def send_to_makecom(
        self, content_list: List[Dict[str, Any]], summaries: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Send content and summaries to Make.com.

        Args:
            content_list: List of content items
            summaries: Optional list of summaries

        Returns:
            List of results
        """
        if not content_list:
            return []

        # Transform data
        transformed_items = self.data_transformer.transform_batch(content_list, summaries)

        # Send to Make.com
        results = []
        for item in transformed_items:
            # Format payload
            payload = self.webhook_handler.format_payload(item)

            # Determine scenario based on content type
            content_type = item.get("ContentType", "unknown")
            scenario = self.make_client.get_scenario_for_content_type(content_type)

            if scenario:
                start_time = time.time()
                response = self.make_client.send_webhook(scenario["webhook_url"], payload)
                duration = time.time() - start_time

                success = self.webhook_handler.validate_response(response)
                self.activity_logger.log_webhook(
                    scenario["webhook_url"], success, duration, None if success else "Validation failed"
                )

                results.append({"item": item.get("Name"), "success": success, "response": response})

        return results

    def run_full_cycle(self) -> Dict[str, Any]:
        """
        Run full monitoring cycle: extract, process, summarize, send.

        Returns:
            Statistics dictionary
        """
        self.logger.info("Starting full monitoring cycle")
        cycle_start = time.time()

        all_content = []
        all_summaries = []
        stats = {
            "sources_processed": 0,
            "content_extracted": 0,
            "summaries_generated": 0,
            "sent_to_makecom": 0,
            "errors": 0,
        }

        # Extract from all enabled sources
        for source in self.sources:
            if not source.get("enabled", True):
                continue

            try:
                items = self.extract_from_source(source.get("source_id"))
                all_content.extend(items)
                stats["sources_processed"] += 1
                stats["content_extracted"] += len(items)
            except Exception as e:
                self.logger.error(f"Error extracting from {source.get('source_id')}: {e}")
                stats["errors"] += 1

        # Process and summarize
        if all_content:
            try:
                summaries = self.process_content(all_content, summarize=True)
                all_summaries = summaries
                stats["summaries_generated"] = len(summaries)
            except Exception as e:
                self.logger.error(f"Error processing content: {e}")
                stats["errors"] += 1

        # Send to Make.com
        if all_content:
            try:
                results = self.send_to_makecom(all_content, all_summaries)
                stats["sent_to_makecom"] = len([r for r in results if r.get("success")])
            except Exception as e:
                self.logger.error(f"Error sending to Make.com: {e}")
                stats["errors"] += 1

        cycle_duration = time.time() - cycle_start
        stats["duration_seconds"] = cycle_duration

        # Log summary
        self.activity_logger.log_summary(
            stats["content_extracted"],
            stats["summaries_generated"],
            stats["errors"],
            self.claude_client.track_usage()["total_cost_usd"],
            cycle_duration,
        )

        self.logger.info(f"Monitoring cycle completed: {stats}")

        return stats


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Content Monitor - Automated content monitoring and summarization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run full monitoring cycle")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test a specific source")
    test_parser.add_argument("--source", required=True, help="Source ID to test")
    test_parser.add_argument("--no-summarize", action="store_true", help="Skip summarization")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate activity report")
    report_parser.add_argument("--days", type=int, default=7, help="Number of days to report")

    # Costs command
    costs_parser = subparsers.add_parser("costs", help="Show cost analysis")
    costs_parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")

    # Summarize command
    summarize_parser = subparsers.add_parser("summarize", help="Summarize a URL")
    summarize_parser.add_argument("--url", required=True, help="URL to summarize")
    summarize_parser.add_argument("--style", default="quick_summary", help="Summary style")

    # Config command
    config_parser = subparsers.add_parser("config", help="Validate configuration")

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Run with scheduler")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize monitor
    monitor = ContentMonitor()

    # Execute command
    if args.command == "run":
        stats = monitor.run_full_cycle()
        print(f"\n✓ Monitoring cycle completed")
        print(f"  Sources: {stats['sources_processed']}")
        print(f"  Content items: {stats['content_extracted']}")
        print(f"  Summaries: {stats['summaries_generated']}")
        print(f"  Sent to Make.com: {stats['sent_to_makecom']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Duration: {stats['duration_seconds']:.2f}s")

    elif args.command == "test":
        print(f"Testing source: {args.source}")
        items = monitor.extract_from_source(args.source)
        print(f"✓ Extracted {len(items)} items")

        if items and not args.no_summarize:
            print(f"Generating summaries...")
            summaries = monitor.process_content(items[:1], summarize=True)
            if summaries:
                print(f"\nSample summary:")
                print(f"  Title: {summaries[0].get('title')}")
                print(f"  Summary: {summaries[0].get('summary')[:200]}...")

    elif args.command == "report":
        print(f"Activity Report (last {args.days} days)")
        print("-" * 50)

        stats = monitor.db.get_stats(days=args.days)
        print(f"Content processed: {stats['content_processed']}")
        print(f"Summaries generated: {stats['summaries_generated']}")
        print(f"Total cost: ${stats['total_cost']:.2f}")
        print(f"Total tokens: {stats['total_tokens']:,}")
        print(f"API calls: {stats['api_calls']}")
        print(f"API errors: {stats['api_errors']}")

    elif args.command == "costs":
        print(f"Cost Analysis (last {args.days} days)")
        print("-" * 50)

        usage = monitor.claude_client.track_usage()
        stats = monitor.db.get_stats(days=args.days)

        print(f"Current session cost: ${usage['total_cost_usd']:.2f}")
        print(f"Historical cost ({args.days} days): ${stats['total_cost']:.2f}")
        print(f"Daily limit: ${usage['cost_limits']['daily_limit']:.2f}")
        print(f"Daily remaining: ${usage['cost_limits']['daily_remaining']:.2f}")

    elif args.command == "summarize":
        print(f"Summarizing URL: {args.url}")

        # Create temporary content item
        from extractors import WebExtractor

        temp_source = {"source_id": "manual", "type": "web", "url": args.url, "enabled": True}
        extractor = WebExtractor(temp_source)

        items = extractor.extract()
        if items:
            summaries = monitor.process_content(items, summarize=True)
            if summaries:
                summary = summaries[0]
                print(f"\n{summary.get('summary')}")
                print(f"\nTokens used: {summary.get('tokens', {}).get('total', 0)}")
                print(f"Cost: ${summary.get('cost_usd', 0):.4f}")

    elif args.command == "config":
        print("Validating configuration...")
        print("-" * 50)

        # Check environment variables
        required_vars = ["ANTHROPIC_API_KEY"]
        optional_vars = ["MAKE_API_KEY", "GMAIL_CREDENTIALS_PATH"]

        print("\nEnvironment Variables:")
        for var in required_vars:
            value = os.getenv(var)
            status = "✓" if value else "✗"
            print(f"  {status} {var}: {'Set' if value else 'Not set'}")

        for var in optional_vars:
            value = os.getenv(var)
            status = "✓" if value else "-"
            print(f"  {status} {var}: {'Set' if value else 'Not set (optional)'}")

        # Validate Make.com
        print("\nMake.com Configuration:")
        make_validation = monitor.make_client.validate_configuration()
        print(f"  Valid: {make_validation['valid']}")
        print(f"  Scenarios: {make_validation['scenario_count']}")
        print(f"  Enabled: {make_validation['enabled_scenario_count']}")

        if make_validation['issues']:
            print(f"  Issues:")
            for issue in make_validation['issues']:
                print(f"    - {issue}")

        # Check Claude API
        print("\nClaude API:")
        try:
            templates = monitor.claude_client.get_available_templates()
            print(f"  ✓ Connected")
            print(f"  Templates: {', '.join(templates)}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        print("\n✓ Configuration validation complete")

    elif args.command == "schedule":
        print("Starting scheduler...")

        scheduler = ContentScheduler()

        # Add source monitors
        for source in monitor.sources:
            if source.get("enabled", True):
                scheduler.add_source_monitor(
                    source.get("source_id"), lambda sid: monitor.extract_from_source(sid)
                )

        # Add daily report
        def daily_report():
            stats = monitor.db.get_stats(days=1)
            print(f"Daily Report: {stats}")

        scheduler.add_daily_task("daily_report", daily_report, "08:00")

        # Add weekly cleanup
        scheduler.add_weekly_task("weekly_cleanup", lambda: monitor.db.cleanup_old_cache(30), "sunday", "00:00")

        print(f"Scheduler started with {len(scheduler.tasks)} tasks")
        print("Press Ctrl+C to stop")

        try:
            scheduler.start(blocking=True)
        except KeyboardInterrupt:
            print("\nStopping scheduler...")
            scheduler.stop()


if __name__ == "__main__":
    main()
