"""Scheduling and automation system."""

import schedule
import time
import logging
import json
from typing import Callable, Dict, Any, List
from datetime import datetime
from threading import Thread


class ContentScheduler:
    """Manage scheduled tasks for content monitoring."""

    def __init__(
        self,
        sources_config_path: str = "config/sources.json",
        enable_scheduler: bool = True,
    ):
        """
        Initialize scheduler.

        Args:
            sources_config_path: Path to sources configuration
            enable_scheduler: Whether scheduling is enabled
        """
        self.logger = logging.getLogger(__name__)
        self.enabled = enable_scheduler
        self.running = False

        # Load sources configuration
        with open(sources_config_path, "r") as f:
            config = json.load(f)
            self.sources = config.get("sources", [])
            self.global_settings = config.get("global_settings", {})

        # Task registry
        self.tasks: Dict[str, Dict[str, Any]] = {}

        self.logger.info(f"Scheduler initialized with {len(self.sources)} sources")

    def add_source_monitor(self, source_id: str, callback: Callable, interval: int = None):
        """
        Add a scheduled monitor for a source.

        Args:
            source_id: ID of source to monitor
            callback: Function to call
            interval: Check interval in seconds (overrides config)
        """
        # Find source in configuration
        source = next((s for s in self.sources if s.get("source_id") == source_id), None)

        if not source:
            self.logger.error(f"Source not found: {source_id}")
            return

        if not source.get("enabled", True):
            self.logger.info(f"Source {source_id} is disabled, skipping")
            return

        # Get interval
        check_interval = interval or source.get(
            "check_interval", self.global_settings.get("default_interval", 3600)
        )

        # Convert to minutes for schedule library
        interval_minutes = check_interval // 60

        # Schedule the job
        if interval_minutes >= 60:
            # Schedule hourly
            hours = interval_minutes // 60
            job = schedule.every(hours).hours.do(callback, source_id=source_id)
        else:
            # Schedule by minutes
            job = schedule.every(interval_minutes).minutes.do(callback, source_id=source_id)

        self.tasks[source_id] = {
            "source": source,
            "callback": callback,
            "interval": check_interval,
            "job": job,
            "last_run": None,
        }

        self.logger.info(f"Scheduled {source_id} to run every {check_interval} seconds")

    def add_daily_task(self, name: str, callback: Callable, time_str: str = "08:00"):
        """
        Add a daily scheduled task.

        Args:
            name: Task name
            callback: Function to call
            time_str: Time to run (HH:MM format)
        """
        job = schedule.every().day.at(time_str).do(callback)

        self.tasks[name] = {
            "type": "daily",
            "callback": callback,
            "time": time_str,
            "job": job,
            "last_run": None,
        }

        self.logger.info(f"Scheduled daily task '{name}' at {time_str}")

    def add_weekly_task(self, name: str, callback: Callable, day: str = "monday", time_str: str = "00:00"):
        """
        Add a weekly scheduled task.

        Args:
            name: Task name
            callback: Function to call
            day: Day of week
            time_str: Time to run (HH:MM format)
        """
        day_schedule = getattr(schedule.every(), day.lower())
        job = day_schedule.at(time_str).do(callback)

        self.tasks[name] = {
            "type": "weekly",
            "callback": callback,
            "day": day,
            "time": time_str,
            "job": job,
            "last_run": None,
        }

        self.logger.info(f"Scheduled weekly task '{name}' on {day} at {time_str}")

    def add_interval_task(self, name: str, callback: Callable, minutes: int):
        """
        Add a task that runs at regular intervals.

        Args:
            name: Task name
            callback: Function to call
            minutes: Interval in minutes
        """
        job = schedule.every(minutes).minutes.do(callback)

        self.tasks[name] = {
            "type": "interval",
            "callback": callback,
            "interval_minutes": minutes,
            "job": job,
            "last_run": None,
        }

        self.logger.info(f"Scheduled interval task '{name}' every {minutes} minutes")

    def remove_task(self, name: str):
        """
        Remove a scheduled task.

        Args:
            name: Task name or source_id
        """
        if name in self.tasks:
            task = self.tasks[name]
            schedule.cancel_job(task["job"])
            del self.tasks[name]
            self.logger.info(f"Removed scheduled task: {name}")
        else:
            self.logger.warning(f"Task not found: {name}")

    def run_pending(self):
        """Run all pending scheduled tasks."""
        schedule.run_pending()

    def start(self, blocking: bool = True):
        """
        Start the scheduler.

        Args:
            blocking: If True, runs in blocking mode. If False, runs in background thread.
        """
        if not self.enabled:
            self.logger.info("Scheduler is disabled")
            return

        self.running = True
        self.logger.info(f"Starting scheduler with {len(self.tasks)} tasks")

        if blocking:
            self._run_loop()
        else:
            thread = Thread(target=self._run_loop, daemon=True)
            thread.start()
            self.logger.info("Scheduler started in background")

    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(10)

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        self.logger.info("Scheduler stopped")

    def get_status(self) -> Dict[str, Any]:
        """
        Get scheduler status.

        Returns:
            Status dictionary
        """
        task_status = []
        for name, task in self.tasks.items():
            task_status.append(
                {
                    "name": name,
                    "type": task.get("type", "source"),
                    "last_run": task.get("last_run"),
                    "next_run": task["job"].next_run.isoformat() if task["job"].next_run else None,
                }
            )

        return {
            "enabled": self.enabled,
            "running": self.running,
            "task_count": len(self.tasks),
            "tasks": task_status,
        }

    def run_now(self, name: str) -> bool:
        """
        Run a specific task immediately.

        Args:
            name: Task name or source_id

        Returns:
            True if successful
        """
        if name not in self.tasks:
            self.logger.error(f"Task not found: {name}")
            return False

        try:
            task = self.tasks[name]
            callback = task["callback"]

            # Call with source_id if it's a source task
            if "source" in task:
                callback(source_id=name)
            else:
                callback()

            task["last_run"] = datetime.utcnow().isoformat()
            self.logger.info(f"Manually executed task: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Error running task {name}: {e}")
            return False

    def get_priority_sources(self) -> List[str]:
        """
        Get list of high-priority source IDs.

        Returns:
            List of source IDs
        """
        priority_sources = [
            s.get("source_id")
            for s in self.sources
            if s.get("enabled") and s.get("priority") == "high"
        ]
        return priority_sources

    def is_quiet_hours(self, quiet_start: str = "22:00", quiet_end: str = "06:00") -> bool:
        """
        Check if current time is within quiet hours.

        Args:
            quiet_start: Start time (HH:MM)
            quiet_end: End time (HH:MM)

        Returns:
            True if within quiet hours
        """
        now = datetime.now().time()

        # Parse times
        start_hour, start_min = map(int, quiet_start.split(":"))
        end_hour, end_min = map(int, quiet_end.split(":"))

        start_time = datetime.now().replace(hour=start_hour, minute=start_min).time()
        end_time = datetime.now().replace(hour=end_hour, minute=end_min).time()

        # Check if quiet hours span midnight
        if start_time > end_time:
            return now >= start_time or now <= end_time
        else:
            return start_time <= now <= end_time
