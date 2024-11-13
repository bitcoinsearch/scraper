import re
from typing import List, Optional
from bs4 import BeautifulSoup, Tag

from scraper.scrapers.scrapy.selector_types import SelectorConfig


class SelectorExtractor:
    """Base class for selector-based content extraction"""

    def process_html(self, element: Tag) -> Tag:
        """Process HTML content before text extraction
        Default implementation - no processing"""
        return element

    def _extract_items(
        self, soup: BeautifulSoup, selector_config: SelectorConfig
    ) -> List[Tag]:
        """Extract items from page using configured selector"""
        return soup.select(selector_config.selector)

    def _extract_field(
        self, item: Tag, selector_config: Optional[SelectorConfig]
    ) -> Optional[str]:
        """Extract a field from an item using configured selector."""
        if not selector_config:
            return None

        element = item.select_one(selector_config.selector)
        if not element:
            return None

        if selector_config.attribute:
            # Get the specified attribute
            value = element.get(selector_config.attribute)
        else:
            # For content fields that might need HTML processing
            processed_element = self.process_html(element)
            value = processed_element.get_text(strip=True)

        # Apply pattern if specified
        if selector_config.pattern and value:
            match = re.search(selector_config.pattern, value)
            if match:
                value = match.group(1) if match.groups() else match.group(0)

        return value.strip() if value else None

    def _extract_links(
        self, soup: BeautifulSoup, selector_config: SelectorConfig
    ) -> List[str]:
        """Extract links using configured selector"""
        elements = soup.select(selector_config.selector)

        if selector_config.attribute:
            links = [el.get(selector_config.attribute) for el in elements]
        else:
            links = [el.get("href") for el in elements]

        links = [link for link in links if link]  # Filter None values

        if selector_config.pattern:
            pattern = re.compile(selector_config.pattern)
            links = [link for link in links if pattern.search(link)]

        return links

    def _extract_next_page(
        self, soup: BeautifulSoup, selector_config: SelectorConfig
    ) -> Optional[str]:
        """Extract next page link using configured selector"""
        if not selector_config:
            return None

        links = self._extract_links(soup, selector_config)
        return links[0] if links else None
