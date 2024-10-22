import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from typing import List, Dict, Any, Optional

from scraper.scrapers import ScrapyBasedScraper, BaseSpider
from scraper.config import settings, SourceConfig
from scraper.registry import scraper_registry


@scraper_registry.register("bitcointalk")
class BitcoinTalkScraper(ScrapyBasedScraper):
    def get_spider_class(self):
        return BitcoinTalkSpider


class BitcoinTalkSpider(BaseSpider):
    name = "bitcointalk"

    def __init__(self, scraper, config: SourceConfig, *args, **kwargs):
        super().__init__(scraper, config, *args, **kwargs)
        self.people_of_interest = self.load_people_of_interest()
        self.filter_by_author = settings.config.getboolean("filter_by_author", True)

        mode = "test" if self.test_resources else "full"
        resources = (
            f"({len(self.test_resources)} resources)" if self.test_resources else ""
        )
        logger.info(
            f"Initializing BitcoinTalk spider in {mode} mode {resources}. "
            f"Domain: {self.allowed_domains[0]}, "
            f"Author filtering: {'enabled' if self.filter_by_author else 'disabled'}"
        )

    def load_people_of_interest(self) -> List[str]:
        """Load list of usernames we want to track."""
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "people_of_interest.json"
        )
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            usernames = [
                person["bitcointalk_username"].lower()
                for person in data
                if "bitcointalk_username" in person
            ]
            logger.info(f"Loaded {len(usernames)} BitcoinTalk usernames of interest")
            return usernames
        except FileNotFoundError:
            logger.warning(f"People of interest file not found at {file_path}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Error parsing people of interest file at {file_path}")
            return []

    def get_resource_links(self, response) -> List[Any]:
        """Extract topic links from the board page."""
        links = response.css("tr > td > span > a")
        return [
            link
            for link in links
            if link.attrib.get("href")
            and link.attrib["href"].startswith(f"{self.config.domain}index.php?topic=")
            and "class" not in link.attrib
        ]

    def get_next_index_page(self, response) -> Optional[str]:
        """Get the URL of the next board page."""
        return response.css("a.navPages:contains('»')::attr(href)").get()

    def get_resource_id(self, response) -> str:
        """Extract the topic ID from the URL."""
        return response.url.split("topic=")[1].split(".")[0]

    def get_items(self, soup: BeautifulSoup) -> List[Any]:
        """Extract posts from the topic page."""
        return soup.select("table.bordercolor > tr > td > table > tr > td.windowbg")

    def get_next_resource_page(self, soup: BeautifulSoup) -> Optional[Any]:
        """Get the next page link for a topic."""
        return soup.find("a", class_="navPages", string="»")

    def parse_item(self, item: Any, resource_url: str) -> Optional[Dict[str, Any]]:
        """
        Parse an individual post.

        Returns None if:
        - Author cannot be determined
        - Author is not in people of interest (when filtering is enabled)
        - Post date cannot be parsed
        """
        try:
            # Extract author
            author = self.get_author(item)
            if not author:
                logger.debug("Skipping post: No author found")
                return None

            # Apply author filter if enabled
            if self.filter_by_author and author.lower() not in self.people_of_interest:
                logger.debug(
                    f"Skipping post: Author {author} not in people of interest"
                )
                return None

            # Extract and validate dates
            date, last_edit_date = self.get_post_date(item)
            if not date:
                logger.debug("Skipping post: Could not parse date")
                return None

            # Get post URL and ID
            post_url = self.get_post_url(item, resource_url)
            post_id = self.extract_post_id(post_url)

            # Build document data
            item_data = {
                "id": f"bitcointalk-{post_id}",
                "authors": [author],
                "body": self.get_post_body(item),
                "body_type": "raw",
                "domain": str(self.config.domain),
                "url": post_url,
                "title": self.get_post_title(item),
                "created_at": date.isoformat(),
                "type": self.determine_post_type(item),
            }

            self.increment_scraped()
            return item_data

        except Exception as e:
            logger.error(f"Error parsing post: {e}")
            logger.debug("Error details:", exc_info=True)
            return None

    def get_author(self, item: BeautifulSoup) -> Optional[str]:
        """Extract the post author."""
        author_elem = item.select_one(".poster_info > b > a")
        if not author_elem:
            return None

        author = author_elem.text.strip()
        if not author:
            return None

        return author

    def get_post_date(self, item: BeautifulSoup) -> Optional[datetime]:
        """
        Extract and parse the post date.

        Handles both formats:
        - "Month DD, YYYY, HH:MM:SS AM/PM"
        - "Month DD, YYYY, HH:MM AM/PM"

        Also handles posts that have been edited, extracting the original post date.
        """

        def parse_date(date_text):
            try:
                return datetime.strptime(date_text, "%B %d, %Y, %I:%M:%S %p")
            except ValueError:
                # Try parsing without seconds
                try:
                    return datetime.strptime(date_text, "%B %d, %Y, %I:%M %p")
                except ValueError:
                    logger.error(f"Unable to parse date: {date_text}")
                    return None

        date_elem = item.select_one(".td_headerandpost .smalltext")
        if not date_elem:
            return None

        date_text = date_elem.text.strip()

        # Handle edited posts
        last_edit_date = None
        if "Last edit:" in date_text:
            original_date_text, last_edit_text = date_text.split("Last edit:")
            date_text = original_date_text.strip()
            last_edit_text = last_edit_text.split(" by ")[0].strip()
            last_edit_date = parse_date(last_edit_text)

        date = parse_date(date_text)
        return date, last_edit_date

    def get_post_url(self, item: BeautifulSoup, resource_url: str) -> str:
        """Get the URL for the post."""
        subject_elem = item.select_one(".subject > a")
        if subject_elem and "href" in subject_elem.attrs:
            return subject_elem["href"]
        return resource_url

    def extract_post_id(self, url: str) -> str:
        """Extract post ID from URL."""
        return url.split("#msg")[-1] if "#msg" in url else ""

    def get_post_body(self, item: BeautifulSoup) -> str:
        """Extract the post body text."""
        body = item.select_one(".post")
        if body:
            # Remove quotes to get original content only
            for tag in body.select(".quoteheader, .quote"):
                tag.decompose()
            return body.text.strip()
        return ""

    def get_post_title(self, item: BeautifulSoup) -> str:
        """Extract the post title."""
        subject_elem = item.select_one(".subject > a")
        return subject_elem.text if subject_elem else ""

    def determine_post_type(self, item: BeautifulSoup) -> str:
        """Determine if this is a topic starter or reply."""
        message_number_elem = item.select_one(".message_number")
        message_number = message_number_elem.text if message_number_elem else ""
        return "topic" if message_number == "#1" else "post"
