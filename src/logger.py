"""Logging configuration and utilities."""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional


def setup_logging(
    log_level: str = None,
    log_dir: str = None,
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console

    Returns:
        Root logger
    """
    # Get log level from environment or parameter
    level_str = log_level or os.getenv("LOG_LEVEL", "INFO")
    level = getattr(logging, level_str.upper(), logging.INFO)

    # Get log directory
    log_directory = log_dir or os.getenv("LOG_DIR", "logs")
    os.makedirs(log_directory, exist_ok=True)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers = []

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handlers
    if log_to_file:
        # Main log file (rotating)
        log_file = os.path.join(log_directory, "content_monitor.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Error log file (errors only)
        error_file = os.path.join(log_directory, "errors.log")
        error_handler = logging.handlers.RotatingFileHandler(
            error_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

    return root_logger


class ActivityLogger:
    """Log activity and metrics."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize activity logger.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.session_start = datetime.utcnow()

    def log_extraction(
        self,
        source_id: str,
        item_count: int,
        duration_seconds: float,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """
        Log content extraction activity.

        Args:
            source_id: Source ID
            item_count: Number of items extracted
            duration_seconds: Time taken
            success: Whether extraction succeeded
            error: Error message if any
        """
        if success:
            self.logger.info(
                f"Extraction [{source_id}]: {item_count} items in {duration_seconds:.2f}s"
            )
        else:
            self.logger.error(
                f"Extraction FAILED [{source_id}]: {error} (duration: {duration_seconds:.2f}s)"
            )

    def log_processing(
        self,
        item_count: int,
        duration_seconds: float,
        tokens_used: int = 0,
        cost_usd: float = 0,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """
        Log content processing activity.

        Args:
            item_count: Number of items processed
            duration_seconds: Time taken
            tokens_used: Total tokens used
            cost_usd: Total cost
            success: Whether processing succeeded
            error: Error message if any
        """
        if success:
            self.logger.info(
                f"Processing: {item_count} items in {duration_seconds:.2f}s "
                f"(tokens: {tokens_used}, cost: ${cost_usd:.4f})"
            )
        else:
            self.logger.error(
                f"Processing FAILED: {error} "
                f"(processed: {item_count}, duration: {duration_seconds:.2f}s)"
            )

    def log_api_call(
        self,
        endpoint: str,
        success: bool,
        duration_seconds: float,
        tokens_used: int = 0,
        cost_usd: float = 0,
        error: Optional[str] = None,
    ):
        """
        Log API call.

        Args:
            endpoint: API endpoint
            success: Whether call succeeded
            duration_seconds: Time taken
            tokens_used: Tokens used
            cost_usd: Cost
            error: Error message if any
        """
        if success:
            self.logger.debug(
                f"API [{endpoint}]: {duration_seconds:.2f}s, "
                f"{tokens_used} tokens, ${cost_usd:.4f}"
            )
        else:
            self.logger.error(f"API FAILED [{endpoint}]: {error} ({duration_seconds:.2f}s)")

    def log_webhook(
        self,
        url: str,
        success: bool,
        duration_seconds: float,
        error: Optional[str] = None,
    ):
        """
        Log webhook call.

        Args:
            url: Webhook URL (truncated)
            success: Whether call succeeded
            duration_seconds: Time taken
            error: Error message if any
        """
        # Truncate URL for logging
        url_display = url[:50] + "..." if len(url) > 50 else url

        if success:
            self.logger.info(f"Webhook [{url_display}]: {duration_seconds:.2f}s")
        else:
            self.logger.error(f"Webhook FAILED [{url_display}]: {error}")

    def log_summary(
        self,
        total_items: int,
        successful: int,
        failed: int,
        total_cost: float,
        duration_seconds: float,
    ):
        """
        Log summary of operations.

        Args:
            total_items: Total items processed
            successful: Successful items
            failed: Failed items
            total_cost: Total cost
            duration_seconds: Total duration
        """
        success_rate = (successful / total_items * 100) if total_items > 0 else 0

        self.logger.info(
            f"Session Summary: {total_items} items, "
            f"{successful} successful ({success_rate:.1f}%), "
            f"{failed} failed, "
            f"${total_cost:.4f} cost, "
            f"{duration_seconds:.2f}s duration"
        )

    def log_cost_alert(self, current_cost: float, limit: float, threshold: float):
        """
        Log cost alert.

        Args:
            current_cost: Current cost
            limit: Cost limit
            threshold: Alert threshold (0-1)
        """
        percentage = (current_cost / limit * 100) if limit > 0 else 0

        if current_cost >= limit:
            self.logger.critical(
                f"COST LIMIT EXCEEDED: ${current_cost:.2f} >= ${limit:.2f} ({percentage:.1f}%)"
            )
        elif current_cost >= limit * threshold:
            self.logger.warning(
                f"APPROACHING COST LIMIT: ${current_cost:.2f} / ${limit:.2f} ({percentage:.1f}%)"
            )

    def log_error_rate_alert(self, error_count: int, total_count: int, threshold: float = 0.1):
        """
        Log error rate alert.

        Args:
            error_count: Number of errors
            total_count: Total operations
            threshold: Alert threshold (0-1)
        """
        if total_count == 0:
            return

        error_rate = error_count / total_count

        if error_rate >= threshold:
            self.logger.warning(
                f"HIGH ERROR RATE: {error_count}/{total_count} "
                f"({error_rate*100:.1f}%) >= {threshold*100:.1f}%"
            )
