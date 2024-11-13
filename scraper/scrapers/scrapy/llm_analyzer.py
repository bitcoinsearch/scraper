from datetime import datetime
from pathlib import Path
import json
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any, Set
from loguru import logger
from openai import AsyncOpenAI
from scraper.models import SourceConfig
from scraper.config import get_project_root, settings
from scraper.scrapers.scrapy.spider_config import SpiderConfig


class LLMAnalyzer:
    """Uses LLM to analyze HTML structure and generate SpiderConfig compatible configurations"""

    # Elements that typically don't contain relevant content
    NOISE_ELEMENTS: Set[str] = {
        "script",
        "style",
        "noscript",
        "iframe",
        "nav",
        "footer",
        "header",
        "banner",
        "aside",
        "svg",
        "img",
        "video",
        "audio",
        "canvas",
        "form",
        "button",
    }

    def __init__(self, source_config: SourceConfig, api_key: str, debug: bool = False):
        """
        Initialize the analyzer with source configuration.

        Args:
            source_config: SourceConfig containing source metadata and analyzer configuration
            api_key: OpenAI API key
            debug: Whether to save debug outputs
        """
        if not source_config.analyzer_config:
            raise ValueError(
                f"No analyzer configuration found for source {source_config.name}"
            )

        self.source_config = source_config
        self.client = AsyncOpenAI(api_key=api_key)
        self.debug = debug
        self.debug_dir = Path("debug_outputs") / self.source_config.name
        if debug:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

        # Initialize SpiderConfig for the source
        config_path = (
            Path(get_project_root())
            / Path("scrapy_sources_configs")
            / f"{self.source_config.name.lower()}.yaml"
        )
        self.spider_config = SpiderConfig(str(config_path), create_if_missing=True)

    async def analyze(self) -> Dict[str, Any]:
        """Analyze source pages and generate selectors configuration"""
        # Analyze index page
        index_analysis = await self._analyze_page(
            str(self.source_config.analyzer_config.index_url), "index"
        )

        # Analyze resource page
        resource_analysis = await self._analyze_page(
            str(self.source_config.analyzer_config.resource_url), "resource"
        )

        # Generate complete configuration
        selector_config = {
            "index_page": self._convert_index_analysis(index_analysis),
            "resource_page": self._convert_resource_analysis(resource_analysis),
        }

        # Update configuration using SpiderConfig
        self.spider_config.update_config(selector_config)

        return selector_config

    def _get_index_page_prompt(self, url: str, html: str) -> str:
        return f"""You are an expert web scraper analyst focusing on content discovery. You are analyzing an index/listing page at: {url}

CONTEXT:
We implement a THREE-LEVEL scraping pattern:
1. INDEX PAGES (current level): List multiple resources (like blog posts or forum threads)
2. RESOURCE PAGES: Individual pages that contain either a single item or multiple items
3. ITEMS: The actual content units within resource pages

For this INDEX PAGE analysis, we need to:
1. Identify links that lead to resource pages
2. Ensure consistent URL patterns for these resource links
3. Find the "Next Page" link to navigate through all index pages

SELECTOR PRIORITY ORDER:
1. IDs (most reliable): e.g., "#post-link", "#next-page"
2. Unique class combinations: e.g., ".post-list .entry-link"
3. Data attributes: e.g., "[data-entry-id]", "[data-page-nav='next']"
4. Structural patterns (last resort): e.g., "article h2 a"

Key Requirements:
- The item_selector must reliably identify links to resource pages
- URL patterns should help validate that we're capturing the right links
- The next_page selector must specifically identify the link to the NEXT page of listings
- If next page link is not found, it must be null
- Be explicit about confidence when elements can't be found

PAGINATION NOTES:
- We specifically need the selector for the "Next Page" link, not all pagination links
- Common patterns for next page links:
  - Text containing "Next", "»", ">" or similar
  - Usually the last or rightmost pagination link
  - May have specific CSS classes like "next-page", "pagination-next"
- Do not include selectors for "Previous", numbered, or other pagination links

Return a JSON object with this structure:
{{
    "items": {{
        "item_selector": {{
            "selector": "CSS selector for resource links",
            "attribute": "href",
            "pattern": "URL pattern to validate resource links (e.g., '/post/\\d+' or '?topic=\\d+')"
        }}
    }},
    "next_page": null | {{
        "selector": "CSS selector SPECIFICALLY for the next page link",
        "attribute": "href"
    }},
    "confidence_scores": {{
        "resource_links": "0-1 score for confidence in resource link selection",
        "next_page": "0-1 score for confidence in next page link selection (0 if not found)",
        "url_pattern": "0-1 score for confidence in URL pattern identification"
    }},
    "explanations": {{
        "resource_links": "Why this selector will reliably identify resource links",
        "pattern": "Why this URL pattern is characteristic of resource pages",
        "next_page": "Why this selector will reliably find the next page link or why it wasn't found"
    }}
}}

IMPORTANT NOTES:
- next_page must be null if no "Next Page" link is found, not an object with null values
- Never return empty strings for selectors
- Confidence scores should be 0 for elements that aren't found
- Make sure the next_page selector is specific to the "Next" link, not all pagination links

Analyze this HTML structure:
{html}

Return only valid JSON without any other text."""

    def _get_resource_page_prompt(self, url: str, html: str) -> str:
        return f"""You are an expert web scraper analyst focusing on content extraction. You are analyzing a resource page at: {url}

CONTEXT:
We implement a THREE-LEVEL scraping pattern:
1. INDEX PAGES: List multiple resources
2. RESOURCE PAGES (current level): Individual pages that contain content
3. ITEMS: The actual content units within resource pages

SELECTOR PRIORITY ORDER:
1. IDs (most reliable): e.g., "#post-content", "#author-name"
2. Unique class combinations: e.g., ".entry-content .main-text"
3. Data attributes: e.g., "[data-author]", "[data-publish-date]"
4. Structural patterns (last resort): e.g., "article .content p"

For this RESOURCE PAGE analysis, we need to determine:
1. Whether this is a single-item resource (like a blog post) or multi-item resource (like a forum thread)
2. How to extract items and their components
3. For multi-item resources, how to navigate to the next page of items

IMPORTANT SELECTOR HIERARCHY:
1. item_selector: Identifies the container for EACH item
   - For single-item pages (like a blog post): Usually "body" or main content area
   - For multi-item pages (like forum threads): Container for EACH individual item
2. Content selectors: Applied WITHIN each item container to extract:
   - Content text
   - Author information
   - Date information
   - Item URL (link to the specific item, if available)
   - Any other metadata
3. next_page selector: For multi-item resources, identifies the link to the next page of items

PAGINATION NOTES:
- Only multi-item resources need next_page selectors
- We specifically need the selector for the "Next Page" link, not all pagination links
- Common patterns for next page links:
  - Text containing "Next", "»", ">" or similar
  - Usually the last or rightmost pagination link
  - May have specific CSS classes like "next-page", "pagination-next"

Return a JSON object with this structure:
{{
    "items": {{
        "item_selector": {{
            "selector": "CSS selector for item container",
            "multiple": boolean,  // true for forum threads, false for blog posts
            "scope_explanation": "Explanation of what this selector captures"
        }},
        "title": null | {{
            "selector": "CSS selector for title WITHIN item container"
        }},
        "content": null | {{
            "selector": "CSS selector for content WITHIN item container"
        }},
        "author": null | {{
            "selector": "CSS selector for author WITHIN item container"
        }},
        "date": null | {{
            "selector": "CSS selector for date WITHIN item container",
        }},
        "url": null | {{
            "selector": "CSS selector for item's permalink/link WITHIN item container",
            "attribute": "href"
        }}
    }},
    "next_page": null | {{
        "selector": "CSS selector SPECIFICALLY for the next page link",
        "attribute": "href"
    }},
    "confidence_scores": {{
        "item_container": "0-1 score for confidence in item container selection",
        "title": "0-1 score for confidence in title selection (0 if not found)",
        "content": "0-1 score for confidence in content selection (0 if not found)",
        "author": "0-1 score for confidence in author selection (0 if not found)",
        "date": "0-1 score for confidence in date selection (0 if not found)",
        "url": "0-1 score for confidence in item URL selection (0 if not found)",
        "next_page": "0-1 score for confidence in next page link selection (0 if not found)"
    }},
    "explanations": {{
        "page_type": "Why this was identified as single/multi-item resource",
        "item_container": "Why this selector reliably identifies item containers",
        "content_selection": "Why content selector was chosen or why it couldn't be found",
        "metadata": "Why author/date/url selectors were chosen or why they couldn't be found",
        "next_page": "Why next page selector was chosen or why it wasn't needed/found",
        "missing_elements": "Explanation for any elements that couldn't be found"
    }}
}}

CRITICAL NOTES:
1. All selectors MUST be relative to item_selector
2. For single-item pages, item_selector defines the main content area
3. For multi-item pages, item_selector must capture EACH individual item container
4. Never return empty strings for selectors
5. If an element can't be found, set the entire field to null (not an object with null values)
6. Confidence scores must be 0 for elements that aren't found
7. Item URL should indicate a permalink or direct link to the specific item, if available
8. next_page selector should ONLY match the link to the next page, not other pagination links

Example of correct null handling:
- If author not found: "author": null
- If no next page link: "next_page": null
- If item URL not found: "url": null

Analyze this HTML structure:
{html}

Return only valid JSON without any other text."""

    async def _analyze_page(self, url: str, page_type: str) -> Dict[str, Any]:
        """Analyze a single page using LLM"""
        # Fetch page content
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()

        # Clean HTML
        cleaned_html = self._clean_html(html)
        self._save_debug("html", page_type, cleaned_html.prettify())

        # Get prompt based on page type
        prompt = (
            self._get_index_page_prompt(url, cleaned_html.prettify())
            if page_type == "index"
            else self._get_resource_page_prompt(url, cleaned_html.prettify())
        )
        self._save_debug("prompt", page_type, {"url": url, "prompt": prompt})

        # Get LLM analysis
        analysis = await self._get_llm_analysis(prompt)
        self._save_debug("analysis", page_type, analysis)

        return analysis

    def _clean_html(self, html: str) -> BeautifulSoup:
        """Remove noise elements from HTML"""
        soup = BeautifulSoup(html, "html.parser")
        for element_type in self.NOISE_ELEMENTS:
            for element in soup.find_all(element_type):
                element.decompose()
        return soup

    async def _get_llm_analysis(self, prompt: str) -> Dict[str, Any]:
        """Get analysis from LLM"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.config.get("chat_completion_model"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert web scraper analyst specializing in CSS selector identification.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error getting LLM analysis: {e}")
            raise

    def _convert_index_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Convert index page analysis to selector configuration format"""
        return {"items": analysis["items"], "next_page": analysis.get("next_page")}

    def _convert_resource_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Convert resource page analysis to selector configuration format"""
        return {"items": analysis["items"], "next_page": analysis.get("next_page")}

    def _save_debug(self, phase: str, page_type: str, content: Any):
        """Save debug information"""
        if not self.debug:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.debug_dir / f"{page_type}_{phase}_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            if isinstance(content, BeautifulSoup):
                json.dump({"html": str(content)}, f, indent=2, ensure_ascii=False)
            else:
                json.dump(content, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved {page_type} {phase} debug output to {filename}")
