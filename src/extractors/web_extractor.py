"""Web page content extractor."""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from .base_extractor import BaseExtractor


class WebExtractor(BaseExtractor):
    """Extractor for web pages."""

    def __init__(self, source_config: Dict[str, Any], cache_manager=None):
        """Initialize web extractor."""
        super().__init__(source_config, cache_manager)
        self.timeout = source_config.get("timeout", 30)
        self.selectors = source_config.get("selectors", {})
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )

    def fetch_content(self) -> List[Dict[str, Any]]:
        """
        Fetch web page content.

        Returns:
            List with single page content (wrapped in list for consistency)
        """
        try:
            headers = {"User-Agent": self.user_agent}
            response = requests.get(self.url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            return [{"html": response.text, "url": self.url}]

        except requests.RequestException as e:
            self.logger.error(f"Error fetching web page {self.url}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching web page: {e}")
            return []

    def parse_content(self, raw_content: Any) -> Dict[str, Any]:
        """
        Parse HTML content into standardized format.

        Args:
            raw_content: Dictionary with HTML and URL

        Returns:
            Standardized content dictionary
        """
        html = raw_content.get("html", "")
        url = raw_content.get("url", self.url)

        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title = self._extract_title(soup)

        # Extract main content
        body = self._extract_body(soup)

        # Extract metadata
        metadata = self._extract_metadata(soup)

        # Detect language
        language = self._detect_language(soup)

        return self.standardize_content(
            title=title,
            body=body,
            url=url,
            metadata=metadata,
            language=language,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try custom selector first
        if "title" in self.selectors:
            title_elem = soup.select_one(self.selectors["title"])
            if title_elem:
                return title_elem.get_text(strip=True)

        # Try standard title tag
        if soup.title:
            return soup.title.get_text(strip=True)

        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return "No Title"

    def _extract_body(self, soup: BeautifulSoup) -> str:
        """Extract main content body."""
        # Try custom selector first
        if "content" in self.selectors:
            content_elem = soup.select_one(self.selectors["content"])
            if content_elem:
                return self._clean_text(content_elem)

        # Remove unwanted elements
        for element in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Try to find main content area
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=lambda x: x and "content" in x.lower())
            or soup.find("body")
        )

        if main_content:
            return self._clean_text(main_content)

        return ""

    def _clean_text(self, element) -> str:
        """Clean and format text from HTML element."""
        # Get text with some structure preserved
        paragraphs = []
        for p in element.find_all(["p", "div", "article", "section"]):
            text = p.get_text(strip=True)
            if text and len(text) > 20:  # Skip very short fragments
                paragraphs.append(text)

        return "\n\n".join(paragraphs) if paragraphs else element.get_text(strip=True)

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata from page."""
        metadata = {}

        # Meta description
        description = soup.find("meta", attrs={"name": "description"})
        if description:
            metadata["description"] = description.get("content", "")

        # Meta keywords
        keywords = soup.find("meta", attrs={"name": "keywords"})
        if keywords:
            metadata["keywords"] = keywords.get("content", "")

        # Author
        author = soup.find("meta", attrs={"name": "author"})
        if author:
            metadata["author"] = author.get("content", "")

        # Open Graph data
        og_title = soup.find("meta", property="og:title")
        if og_title:
            metadata["og_title"] = og_title.get("content", "")

        return metadata

    def _detect_language(self, soup: BeautifulSoup) -> str:
        """Detect page language."""
        # Check html lang attribute
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            lang = html_tag.get("lang", "")
            if "he" in lang.lower():
                return "he"
            elif "en" in lang.lower():
                return "en"

        # Check meta content-language
        meta_lang = soup.find("meta", attrs={"http-equiv": "content-language"})
        if meta_lang:
            lang = meta_lang.get("content", "").lower()
            if "he" in lang:
                return "he"
            elif "en" in lang:
                return "en"

        return "unknown"
