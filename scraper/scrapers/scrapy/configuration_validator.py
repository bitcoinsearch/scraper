import asyncio
import aiohttp
from bs4 import BeautifulSoup, Tag
from typing import Dict, Any
from loguru import logger
from urllib.parse import urljoin

from scraper.scrapers.scrapy.selector_extractor import SelectorExtractor
from scraper.scrapers.scrapy.selector_types import (
    ScrapingConfig,
    ItemConfig,
    SelectorConfig,
)


class ConfigurationValidator(SelectorExtractor):
    """
    Validator that closely mirrors spider behavior and
    collects only essential information for visualization.
    """

    def __init__(
        self,
        source_name: str,
        source_url: str,
        resource_url: str,
        scraping_config: ScrapingConfig,
        max_pages: int = 2,
        page_delay: float = 1.0,
    ):
        self.source_name = source_name
        self.source_url = source_url
        self.resource_url = resource_url
        self.scraping_config = scraping_config
        self.max_pages = max_pages
        self.page_delay = page_delay

    async def validate(self) -> Dict[str, Any]:
        """Validate configuration and collect results"""
        async with aiohttp.ClientSession() as session:
            # Validate index page
            index_results = await self._validate_page_type(
                session=session,
                start_url=self.source_url,
                config=self.scraping_config.index_page,
                page_type="index",
            )

            # Add delay between validations
            await asyncio.sleep(self.page_delay)

            # Validate resource page
            resource_results = await self._validate_page_type(
                session=session,
                start_url=self.resource_url,
                config=self.scraping_config.resource_page,
                page_type="resource",
            )

            return {
                "source_name": self.source_name,
                "index_results": index_results,
                "resource_results": resource_results,
            }

    async def _validate_page_type(
        self,
        session: aiohttp.ClientSession,
        start_url: str,
        config: Any,
        page_type: str,
    ) -> Dict[str, Any]:
        """Validate a specific page type (index or resource)"""
        results = {
            "start_url": start_url,  # Add starting URL
            "items": {
                "selector": config.items.item_selector.selector,
                "count": 0,
                "fields": {},
            },
            "pagination": {
                "selector": config.next_page.selector if config.next_page else None,
                "pages_validated": 0,
                "urls": [],  # Track URLs in pagination chain
            },
            "errors": [],
        }

        try:
            # Follow pagination chain
            current_url = start_url
            pages_validated = 0

            while current_url and pages_validated < self.max_pages:
                # Add URL to pagination chain
                results["pagination"]["urls"].append(current_url)

                page_data = await self._validate_single_page(
                    session, current_url, config, page_type
                )

                # Update results with page data
                if pages_validated == 0:  # Only store fields from first page
                    results["items"]["count"] = page_data["items_count"]
                    results["items"]["fields"] = page_data["fields"]
                    if page_data["errors"]:
                        results["errors"].extend(page_data["errors"])

                pages_validated += 1
                results["pagination"]["pages_validated"] = pages_validated

                # Handle pagination
                if not config.next_page or not page_data["next_url"]:
                    break

                current_url = urljoin(current_url, page_data["next_url"])
                await asyncio.sleep(self.page_delay)

        except Exception as e:
            results["errors"].append(f"Error validating {page_type} page: {str(e)}")
            logger.error(f"Validation error: {str(e)}")

        return results

    async def _validate_single_page(
        self, session: aiohttp.ClientSession, url: str, config: Any, page_type: str
    ) -> Dict[str, Any]:
        """Validate a single page and extract necessary data"""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {
                        "items_count": 0,
                        "fields": {},
                        "next_url": None,
                        "errors": [f"HTTP {response.status} error fetching {url}"],
                    }

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Extract items
                items = self._extract_items(soup, config.items.item_selector)
                items_count = len(items)

                # Extract fields from first item
                fields = {}
                if items:
                    first_item = items[0]
                    fields = self._extract_fields(first_item, config.items)

                # Extract next page URL if configured
                next_url = None
                if config.next_page:
                    next_elements = soup.select(config.next_page.selector)
                    if next_elements:
                        next_url = next_elements[0].get(config.next_page.attribute)

                return {
                    "items_count": items_count,
                    "fields": fields,
                    "next_url": next_url,
                    "errors": [],
                }

        except Exception as e:
            return {
                "items_count": 0,
                "fields": {},
                "next_url": None,
                "errors": [str(e)],
            }

    def _validate_field_extraction(
        self, item: Tag, config: SelectorConfig, field_name: str
    ) -> Dict[str, Any]:
        """
        Validate field extraction and provide detailed feedback.
        This wrapper helps track the validation process while using shared extraction logic.
        """
        try:
            value = self._extract_field(item, config).text
            if value:
                # Special handling for content field samples
                if field_name == "content" and len(value) > 100:
                    start = value[:50].rstrip()
                    end = value[-50:].lstrip()
                    sample = f"{start}...{end}"
                else:
                    sample = value[:100]  # Truncate other fields normally

                return {"sample": sample, "selector": config.selector}
            return {"error": "No content extracted", "selector": config.selector}
        except Exception as e:
            return {"error": str(e), "selector": config.selector}

    def _extract_fields(
        self, item: Tag, config: ItemConfig
    ) -> Dict[str, Dict[str, str]]:
        """Extract and validate fields from an item using shared extraction logic."""
        fields = {}
        field_configs = {
            "title": config.title,
            "author": config.author,
            "date": config.date,
            "content": config.content,
            "url": config.url,
        }

        for field_name, field_config in field_configs.items():
            if not field_config:
                continue

            fields[field_name] = self._validate_field_extraction(
                item, field_config, field_name
            )

        return fields
