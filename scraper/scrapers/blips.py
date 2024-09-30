from typing import Dict, Any

from scraper.scrapers.github import GithubScraper
from scraper.registry import scraper_registry


@scraper_registry.register("blips")
class BLIPsScraper(GithubScraper):
    FRONT_MATTER_START = FRONT_MATTER_END = "```"

    def get_title(self, metadata: Dict[str, Any], body: str) -> str:
        if "bLIP" in metadata:
            return f"bLIP{metadata['bLIP']}: {super().get_title(metadata, body)}"
        return super().get_title(metadata, body)
