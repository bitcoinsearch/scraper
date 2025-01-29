from pathlib import Path
from typing import Dict, Any
from urllib.parse import urljoin

from scraper.scrapers.github import GithubScraper
from scraper.registry import scraper_registry


@scraper_registry.register("BitcoinOps")
class BitcoinOpsScraper(GithubScraper):
    def get_url(self, file_path: str, metadata: Dict[str, Any]) -> str:
        document_type = self.determine_document_type(file_path)

        if document_type == "topic":
            # Extract the file name without extension
            file_name = Path(file_path).stem
            return urljoin(str(self.config.domain), f"en/topics/{file_name}")
        else:
            # For other types, use the default behavior
            return super().get_url(file_path, metadata)
