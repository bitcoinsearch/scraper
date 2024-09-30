from typing import Dict, Any

from scraper.scrapers.github import GithubScraper
from scraper.registry import scraper_registry


@scraper_registry.register("bips")
class BIPsScraper(GithubScraper):
    FRONT_MATTER_START = "<pre>"
    FRONT_MATTER_END = "</pre>"

    def get_title(self, metadata: Dict[str, Any], body: str) -> str:
        if "BIP" in metadata:
            return f"BIP{metadata['BIP']}: {super().get_title(metadata, body)}"
        return super().get_title(metadata, body)

    def is_valid_file_type(self, file_path: str) -> bool:
        return file_path.endswith((".mediawiki", ".md")) and "bip-" in file_path.lower()
