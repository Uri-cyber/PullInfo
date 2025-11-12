"""SQLite database manager for caching and logging."""

import sqlite3
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from contextlib import contextmanager


class DatabaseManager:
    """Manage SQLite database for content caching and logging."""

    def __init__(self, db_path: str = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or os.getenv("DB_PATH", "cache/content_monitor.db")
        self.logger = logging.getLogger(__name__)

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Initialize database
        self._init_database()

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            SQLite connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Content cache table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS content_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE NOT NULL,
                    source_id TEXT NOT NULL,
                    title TEXT,
                    url TEXT,
                    original_content TEXT,
                    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'processed',
                    metadata TEXT
                )
            """
            )

            # Summaries table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id INTEGER,
                    content_hash TEXT,
                    summary_text TEXT NOT NULL,
                    summary_style TEXT,
                    language TEXT,
                    word_count INTEGER,
                    tokens_used INTEGER,
                    cost REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (content_id) REFERENCES content_cache (id)
                )
            """
            )

            # API logs table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    request_data TEXT,
                    response_data TEXT,
                    tokens_input INTEGER,
                    tokens_output INTEGER,
                    cost REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error TEXT,
                    success INTEGER DEFAULT 1
                )
            """
            )

            # Processing queue table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processing_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT NOT NULL,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON content_cache(content_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_id ON content_cache(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_date ON content_cache(processed_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_summary_content_hash ON summaries(content_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_timestamp ON api_logs(timestamp)")

            self.logger.info("Database initialized successfully")

    def is_cached(self, content_hash: str) -> bool:
        """
        Check if content is already cached.

        Args:
            content_hash: Hash of content

        Returns:
            True if cached, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM content_cache WHERE content_hash = ?", (content_hash,))
            return cursor.fetchone() is not None

    def store(self, content_hash: str, content: Dict[str, Any]) -> int:
        """
        Store content in cache.

        Args:
            content_hash: Hash of content
            content: Content dictionary

        Returns:
            ID of stored content
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO content_cache
                (content_hash, source_id, title, url, original_content, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    content_hash,
                    content.get("source_id", "unknown"),
                    content.get("title", ""),
                    content.get("url", ""),
                    json.dumps(content),
                    json.dumps(content.get("metadata", {})),
                ),
            )

            return cursor.lastrowid

    def store_summary(self, content_hash: str, summary: Dict[str, Any]) -> int:
        """
        Store summary in database.

        Args:
            content_hash: Hash of original content
            summary: Summary dictionary

        Returns:
            ID of stored summary
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get content_id
            cursor.execute("SELECT id FROM content_cache WHERE content_hash = ?", (content_hash,))
            row = cursor.fetchone()
            content_id = row[0] if row else None

            cursor.execute(
                """
                INSERT INTO summaries
                (content_id, content_hash, summary_text, summary_style, language,
                 word_count, tokens_used, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    content_id,
                    content_hash,
                    summary.get("summary", ""),
                    summary.get("style", ""),
                    summary.get("language", ""),
                    len(summary.get("summary", "").split()),
                    summary.get("tokens", {}).get("total", 0),
                    summary.get("cost_usd", 0),
                ),
            )

            return cursor.lastrowid

    def log_api_call(
        self,
        endpoint: str,
        request_data: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost: float = 0,
        error: Optional[str] = None,
    ) -> int:
        """
        Log API call.

        Args:
            endpoint: API endpoint
            request_data: Request data
            response_data: Response data
            tokens_input: Input tokens used
            tokens_output: Output tokens used
            cost: Cost in USD
            error: Error message if any

        Returns:
            Log entry ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO api_logs
                (endpoint, request_data, response_data, tokens_input, tokens_output,
                 cost, error, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    endpoint,
                    json.dumps(request_data),
                    json.dumps(response_data) if response_data else None,
                    tokens_input,
                    tokens_output,
                    cost,
                    error,
                    1 if not error else 0,
                ),
            )

            return cursor.lastrowid

    def get_cached_content(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached content by hash.

        Args:
            content_hash: Content hash

        Returns:
            Content dictionary or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT original_content FROM content_cache WHERE content_hash = ?",
                (content_hash,),
            )
            row = cursor.fetchone()

            if row:
                return json.loads(row[0])
            return None

    def get_summary_for_content(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get summary for content.

        Args:
            content_hash: Content hash

        Returns:
            Summary dictionary or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT summary_text, summary_style, language, word_count,
                       tokens_used, cost, created_at
                FROM summaries
                WHERE content_hash = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (content_hash,),
            )
            row = cursor.fetchone()

            if row:
                return {
                    "summary": row[0],
                    "style": row[1],
                    "language": row[2],
                    "word_count": row[3],
                    "tokens_used": row[4],
                    "cost": row[5],
                    "created_at": row[6],
                }
            return None

    def cleanup_old_cache(self, days: int = 30):
        """
        Clean up cache older than specified days.

        Args:
            days: Number of days to keep
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Delete old summaries first (foreign key)
            cursor.execute(
                """
                DELETE FROM summaries
                WHERE content_id IN (
                    SELECT id FROM content_cache
                    WHERE processed_date < ?
                )
            """,
                (cutoff_date,),
            )

            # Delete old content
            cursor.execute("DELETE FROM content_cache WHERE processed_date < ?", (cutoff_date,))

            # Delete old API logs
            cursor.execute("DELETE FROM api_logs WHERE timestamp < ?", (cutoff_date,))

            deleted = cursor.rowcount
            self.logger.info(f"Cleaned up {deleted} old records")

    def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get database statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Statistics dictionary
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Count content
            cursor.execute(
                "SELECT COUNT(*) FROM content_cache WHERE processed_date >= ?",
                (cutoff_date,),
            )
            content_count = cursor.fetchone()[0]

            # Count summaries
            cursor.execute(
                "SELECT COUNT(*), SUM(cost), SUM(tokens_used) FROM summaries WHERE created_at >= ?",
                (cutoff_date,),
            )
            summary_stats = cursor.fetchone()

            # API call stats
            cursor.execute(
                """
                SELECT COUNT(*), SUM(cost), SUM(tokens_input), SUM(tokens_output),
                       SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END)
                FROM api_logs WHERE timestamp >= ?
            """,
                (cutoff_date,),
            )
            api_stats = cursor.fetchone()

            return {
                "period_days": days,
                "content_processed": content_count,
                "summaries_generated": summary_stats[0] or 0,
                "total_cost": (summary_stats[1] or 0) + (api_stats[1] or 0),
                "total_tokens": (summary_stats[2] or 0) + (api_stats[2] or 0) + (api_stats[3] or 0),
                "api_calls": api_stats[0] or 0,
                "api_errors": api_stats[4] or 0,
            }
