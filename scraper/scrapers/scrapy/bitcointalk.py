from datetime import datetime
from bs4 import Tag
from loguru import logger
from typing import Optional

from scraper.scrapers import ScrapyScraper
from scraper.registry import scraper_registry
from scraper.scrapers.scrapy.spider_base import BaseSpider


@scraper_registry.register("bitcointalk")
class BitcoinTalkScraper(ScrapyScraper):
    def get_spider_class(self):
        return BitcoinTalkSpider


class BitcoinTalkSpider(BaseSpider):
    def _get_thread_url(self, url: str) -> str:
        return url.rsplit(".", 1)[0]

    def parse_date(self, date_text: str) -> Optional[str]:
        """
        Parse a date string from various forum post formats.

        Handles formats:
        - "Month DD, YYYY, HH:MM:SS AM/PM"
        - "Month DD, YYYY, HH:MM AM/PM"
        - "Today at HH:MM:SS AM/PM"
        - Also handles dates from edited posts by extracting the original date

        Args:
            date_text: The date string to parse

        Returns:
            Optional[datetime]: The parsed datetime object, or None if parsing fails
        """

        def _parse_date_format(text: str) -> Optional[str]:
            # Handle "Today" format
            if text.startswith("Todayat"):
                try:
                    time_str = text.replace("Todayat ", "").strip()
                    today = datetime.now()
                    time = datetime.strptime(time_str, "%I:%M:%S %p").time()
                    return datetime.combine(today.date(), time).isoformat()
                except ValueError:
                    logger.error(f"Unable to parse 'Today' date: {text}")
                    return None

            # Handle standard formats
            try:
                return datetime.strptime(text, "%B %d, %Y, %I:%M:%S %p").isoformat()
            except ValueError:
                try:
                    return datetime.strptime(text, "%B %d, %Y, %I:%M %p").isoformat()
                except ValueError:
                    logger.error(f"Unable to parse date: {text}")
                    return None

        # Handle edited posts by extracting original date
        if "Last edit:" in date_text:
            original_date_text = date_text.split("Last edit:")[0].strip()
            return _parse_date_format(original_date_text)

        return _parse_date_format(date_text)

    def process_html(self, element: Tag) -> Tag:
        """Process HTML content for BitcoinTalk posts."""
        # Remove quotes to get original content only
        for tag in element.select(".quoteheader, .quote"):
            tag.decompose()
        return element
