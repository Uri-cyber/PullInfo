"""Email content extractor (Gmail API)."""

import os
import base64
from typing import Dict, List, Any, Optional
from .base_extractor import BaseExtractor


class EmailExtractor(BaseExtractor):
    """Extractor for Gmail messages."""

    def __init__(self, source_config: Dict[str, Any], cache_manager=None):
        """Initialize email extractor."""
        super().__init__(source_config, cache_manager)
        self.credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
        self.filters = source_config.get("filters", {})
        self.label = self.filters.get("label", "INBOX")
        self.service = None

    def _get_gmail_service(self):
        """
        Get Gmail API service.

        Returns:
            Gmail API service object

        Note: This requires google-api-python-client to be installed
        and credentials to be set up. This is optional functionality.
        """
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

            creds = None
            if os.path.exists("token.json"):
                creds = Credentials.from_authorized_user_file("token.json", SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.credentials_path or not os.path.exists(self.credentials_path):
                        raise FileNotFoundError(
                            "Gmail credentials not found. "
                            "Please set GMAIL_CREDENTIALS_PATH in .env"
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                with open("token.json", "w") as token:
                    token.write(creds.to_json())

            service = build("gmail", "v1", credentials=creds)
            return service

        except ImportError:
            self.logger.error(
                "Gmail API libraries not installed. "
                "Run: pip install google-api-python-client google-auth-httplib2 "
                "google-auth-oauthlib"
            )
            return None
        except Exception as e:
            self.logger.error(f"Error setting up Gmail API: {e}")
            return None

    def fetch_content(self) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from Gmail.

        Returns:
            List of email message objects
        """
        try:
            if not self.service:
                self.service = self._get_gmail_service()

            if not self.service:
                self.logger.error("Gmail service not available")
                return []

            # Build query
            query = "is:unread"
            if self.label and self.label != "INBOX":
                query += f" label:{self.label}"

            # Get message list
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=50)
                .execute()
            )

            messages = results.get("messages", [])

            # Fetch full message details
            full_messages = []
            for msg in messages:
                try:
                    message = (
                        self.service.users()
                        .messages()
                        .get(userId="me", id=msg["id"], format="full")
                        .execute()
                    )
                    full_messages.append(message)
                except Exception as e:
                    self.logger.error(f"Error fetching message {msg['id']}: {e}")

            return full_messages

        except Exception as e:
            self.logger.error(f"Error fetching emails: {e}")
            return []

    def parse_content(self, raw_content: Any) -> Dict[str, Any]:
        """
        Parse Gmail message into standardized format.

        Args:
            raw_content: Gmail message object

        Returns:
            Standardized content dictionary
        """
        # Extract headers
        headers = {h["name"]: h["value"] for h in raw_content.get("payload", {}).get("headers", [])}

        title = headers.get("Subject", "No Subject")
        sender = headers.get("From", "Unknown")
        date = headers.get("Date", "")

        # Extract body
        body = self._extract_body(raw_content.get("payload", {}))

        # Create metadata
        metadata = {
            "from": sender,
            "to": headers.get("To", ""),
            "date": date,
            "message_id": raw_content.get("id"),
            "thread_id": raw_content.get("threadId"),
            "labels": raw_content.get("labelIds", []),
        }

        return self.standardize_content(
            title=title,
            body=body,
            url=f"https://mail.google.com/mail/u/0/#inbox/{raw_content.get('id')}",
            metadata=metadata,
            language=self._detect_language(body),
        )

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload."""
        body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
                        break
                elif part.get("mimeType") == "text/html" and not body:
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8")

        return body

    def _detect_language(self, text: str) -> str:
        """Simple language detection."""
        has_hebrew = any("\u0590" <= char <= "\u05ff" for char in text)
        has_english = any("a" <= char <= "z" for char in text.lower())

        if has_hebrew and has_english:
            return "mixed"
        elif has_hebrew:
            return "he"
        elif has_english:
            return "en"
        else:
            return "unknown"

    def mark_as_processed(self, message_id: str) -> bool:
        """
        Mark email as read/processed.

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful
        """
        try:
            if not self.service:
                return False

            self.service.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()

            return True

        except Exception as e:
            self.logger.error(f"Error marking message as read: {e}")
            return False
