import re
from typing import List, Optional
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass

from scraper.scrapers.scrapy.selector_types import SelectorConfig


@dataclass
class FieldExtractionResult:
    """Result of field extraction containing both processed text and original content."""

    text: Optional[str]
    processed_html: Optional[str]
    original_html: Optional[str]

    @classmethod
    def from_attribute(cls, value: str) -> "FieldExtractionResult":
        """Create a result from an attribute value where both text and original are the same."""
        stripped = value.strip()
        return cls(text=stripped, processed_html=stripped, original_html=stripped)

    @classmethod
    def none(cls) -> "FieldExtractionResult":
        """Create an empty result."""
        return cls(text=None, processed_html=None, original_html=None)


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
    ) -> FieldExtractionResult:
        """
        Extract a field from an item using configured selector.

        Args:
            item: The BeautifulSoup Tag to extract from
            selector_config: Configuration for the selector

        Returns:
        FieldExtractionResult: Extraction result containing text, processed HTML, and original HTML.
        If no content is found, returns an empty result (use .text to get None).
        """
        if not selector_config:
            return FieldExtractionResult.none()

        element = item.select_one(selector_config.selector)
        if not element:
            return FieldExtractionResult.none()

        if selector_config.attribute:
            # Get the specified attribute
            value = element.get(selector_config.attribute)
            if not value:
                return FieldExtractionResult.none()
            return FieldExtractionResult.from_attribute(value)
        else:
            # For content fields that might need HTML processing
            # Store original HTML before any processing
            original_html = str(element)

            # Process the HTML
            processed_element = self.process_html(element)
            processed_html = str(processed_element)

            # Extract text from processed HTML
            text_value = processed_element.get_text(strip=True)

            # Apply pattern if specified
            if selector_config.pattern and text_value:
                match = re.search(selector_config.pattern, text_value)
                if match:
                    text_value = match.group(1) if match.groups() else match.group(0)

            if not text_value:
                return FieldExtractionResult.none()

            return FieldExtractionResult(
                text=text_value.strip(),
                processed_html=processed_html,
                original_html=original_html,
            )

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
