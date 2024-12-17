import os
from typing import Dict, Any, Set, Type
from urllib.parse import urljoin

from scraper.models.documents import PRReviewClubDocument, ScrapedDocument
from scraper.scrapers.github import GithubScraper
from scraper.registry import scraper_registry
from scraper.utils import slugify


@scraper_registry.register("PR-Review-Club")
class PRReviewClubScraper(GithubScraper):
    # Predefined topics for non-Bitcoin Core meetings
    KNOWN_TOPICS: Set[str] = {
        "rc-testing",
        "bitcoin-inquisition",
        "libsecp256k1",
        "minisketch",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_class: Type[ScrapedDocument] = PRReviewClubDocument

    def _extract_title_from_jekyll_filename(self, file_path: str) -> str:
        """
        Extract the title portion from a Jekyll filename (YYYY-MM-DD-title.md).
        Helper method used for both URL generation and ID generation.
        """
        file_name = os.path.basename(file_path)
        name_without_extension = os.path.splitext(file_name)[0]
        # Split on first three hyphens to separate date components from title
        parts = name_without_extension.split("-", 3)
        return slugify(parts[3])

    def get_url(self, file_path: str, metadata: Dict[str, Any]) -> str:
        if "permalink" in metadata:
            url_path = metadata["permalink"]
        else:
            url_path = self._extract_title_from_jekyll_filename(file_path)
        return urljoin(str(self.config.domain), url_path)

    def generate_id(self, file_path: str) -> str:
        title = self._extract_title_from_jekyll_filename(file_path)
        return f"{self.config.name.lower()}-{title}"

    def customize_document(
        self, document_data: Dict[str, Any], file_path: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Customize document data based on metadata and file information.
        For Bitcoin Core PRs, uses PR number and metadata.
        For other content, identifies topics from filename.
        """
        document_data["number"] = metadata.get("pr", None)
        document_data["host"] = metadata.get("host", [])
        document_data["tags"] = metadata.get("components", []) or []

        # If no PR number exists, this is not a Bitcoin Core PR review
        if not document_data["number"]:
            # Extract title from filename
            title = self._extract_title_from_jekyll_filename(file_path)

            # Find matching topics
            matching_topics = [topic for topic in self.KNOWN_TOPICS if topic in title]

            if not matching_topics:
                raise ValueError(
                    f"File '{file_path}' is not related to Bitcoin Core PR"
                    f"doesn't match any known topics"
                )

            # Add matched topics to tags
            if isinstance(document_data["tags"], list):
                document_data["tags"].extend(list(matching_topics))
            else:
                document_data["tags"] = list(matching_topics)

        return document_data
