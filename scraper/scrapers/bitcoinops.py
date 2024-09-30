import os
from typing import Dict, Any

from scraper.scrapers.github import GithubScraper
from scraper.registry import scraper_registry


@scraper_registry.register("BitcoinOps")
class BitcoinOpsScraper(GithubScraper):
    def get_url(self, file_path: str, metadata: Dict[str, Any]) -> str:
        base_url = self.config.domain
        document_type = self.determine_document_type(file_path)

        if document_type == "topic":
            # Extract the file name without extension
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            return f"{base_url}/en/topics/{file_name}"
        else:
            # For other types, use the default behavior
            return super().get_url(file_path, metadata)
