from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import html
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from loguru import logger

from scraper.models.documents import StackExchangeDocument
from scraper.registry import scraper_registry
from scraper.scrapers.base import BaseScraper


@scraper_registry.register("StackExchange")
class StackExchangeScraper(BaseScraper):
    """
    Scraper for retrieving and processing posts from Bitcoin StackExchange using their API.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_size = 15

        # Calculate date range (last 7 days)
        current_time = datetime.now()
        self.to_timestamp = int(current_time.timestamp())
        self.from_timestamp = int((current_time - timedelta(days=7)).timestamp())

        # Common request headers
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def _unescape_text(self, text: str) -> str:
        """Handle unicode escape sequences and HTML entities."""
        if not text:
            return ""

        # Convert Unicode escape sequences
        text = text.encode().decode("unicode_escape")
        # Unescape HTML entities
        text = html.unescape(text)

        return text.strip()

    async def scrape(self):
        """Main scraping method that orchestrates the API calls and processing."""
        try:
            # Get total number of posts to process
            total_posts = self._get_total_posts()
            total_pages = max(1, (total_posts + self.page_size - 1) // self.page_size)
            self.resources_to_process = total_posts
            logger.info(f"Found {total_posts} posts across {total_pages} pages")

            # Process each page
            for page in range(1, total_pages + 1):
                posts = self._fetch_page(page)
                for post in posts:
                    document = self._process_post(post)
                    if document:
                        await self.process_and_index_document(document)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            logger.exception("Full traceback:")

    def _get_total_posts(self) -> int:
        """Get the total number of posts for the date range."""
        url = f"{self.config.url}/posts"
        params = {
            "site": "bitcoin.stackexchange",
            "filter": "total",
            "fromdate": self.from_timestamp,
            "todate": self.to_timestamp,
        }

        response = requests.get(url, params=params, headers=self.headers, timeout=90)
        if response.status_code == 200:
            data = response.json()
            return data.get("total", 0)
        raise Exception(f"API request failed with status {response.status_code}")

    def _fetch_page(self, page: int) -> list:
        """Fetch a single page of posts from the API."""
        url = f"{self.config.url}/posts"
        params = {
            "site": "bitcoin.stackexchange",
            "filter": "!6WPIomnA_rhBb",  # Filter for titles, body, and body_markdown
            "fromdate": self.from_timestamp,
            "todate": self.to_timestamp,
            "page": page,
            "pagesize": self.page_size,
        }

        response = requests.get(url, params=params, headers=self.headers, timeout=90)
        if response.status_code == 200:
            data = response.json()
            return data.get("items", [])
        raise Exception(f"API request failed with status {response.status_code}")

    def _get_post_details(self, url: str) -> Dict[str, Any]:
        """
        Fetch additional post details from the webpage.
        TODO: get this information from the API instead of scraping
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=60)
            if response.status_code != 200:
                return {}

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract accepted answer ID if available
            accepted_answer = soup.find("div", {"itemprop": "acceptedAnswer"})
            accepted_answer_id = (
                accepted_answer.get("data-answerid") if accepted_answer else None
            )

            # Extract tags - use set to remove duplicates then convert back to list
            tags = list(
                set(tag.text for tag in soup.find_all("a", {"class": "post-tag"}))
            )

            # Get the canonical thread URL (works for both questions and answers)
            thread_link = soup.find("a", title="Short permalink to this question")
            thread_url = (
                urljoin(str(self.config.domain), thread_link["href"])
                if thread_link
                else None
            )

            return {
                "accepted_answer_id": accepted_answer_id,
                "tags": tags,
                "thread_url": thread_url,
            }
        except Exception as e:
            logger.error(f"Error fetching post details: {e}")
            return {}

    def _process_post(self, post: Dict[str, Any]) -> Optional[StackExchangeDocument]:
        """Process a single post and convert it to a StackExchangeDocument."""
        try:
            post_id = post.get("post_id")
            if not post_id:
                return None

            url = post.get("link")
            details = self._get_post_details(url)

            # Get author information
            author = post.get("owner", {}).get("display_name")

            # Get original content and convert body to markdown
            body_markdown = self._unescape_text(post.get("body_markdown", ""))
            original = {
                "format": "html",
                "body": post.get("body", ""),  # Original HTML content from the API
            }

            # Basic document data
            doc_data = {
                "id": f"stackexchange-{post_id}",
                "title": self._unescape_text(post.get("title", "")),
                "body": body_markdown,
                "original": original,
                "authors": [author] if author else None,
                "domain": str(self.config.domain),
                "url": url,  # Use API-provided URL for both questions and answers
                "thread_url": details.get("thread_url", None),
                "created_at": datetime.fromtimestamp(
                    post.get("creation_date", 0)
                ).isoformat(),
                "indexed_at": datetime.now(timezone.utc).isoformat(),
                "tags": details.get("tags"),
                "type": post.get("post_type"),
            }

            # Add accepted answer ID if available
            if doc_data["type"] == "question" and details.get("accepted_answer_id"):
                doc_data["accepted_answer_id"] = details["accepted_answer_id"]

            return StackExchangeDocument(**doc_data)

        except Exception as e:
            logger.error(f"Error processing post {post.get('post_id')}: {e}")
            logger.exception("Full traceback:")
            return None
