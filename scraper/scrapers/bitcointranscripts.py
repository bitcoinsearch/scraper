import re
import os
from typing import Dict, Any, Type
from urllib.parse import urljoin

from scraper.models import BitcoinTranscriptDocument, ScrapedDocument
from scraper.scrapers.github import GithubScraper
from scraper.registry import scraper_registry


@scraper_registry.register("BitcoinTranscripts")
class BitcoinTranscriptsScraper(GithubScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_excluded_files(["_index.md", "STYLE.md"])
        self.document_class: Type[ScrapedDocument] = BitcoinTranscriptDocument

    def is_relevant_file(self, file_path: str) -> bool:
        file_name = os.path.basename(file_path)

        # Exclude language-specific index files (e.g., _index.es.md)
        if re.match(r"^_index\.[a-z]{2}\.md$", file_name):
            return False

        # Then, apply the default GitHub scraper rules
        return super().is_relevant_file(file_path)

    def customize_document(
        self, document_data: Dict[str, Any], file_path: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        document_data["media"] = metadata.get("media", None)
        document_data["authors"] = metadata.get("speakers", [])
        document_data["transcript_by"] = metadata.get("transcript_by", None)
        document_data["needs_review"] = "--needs-review" in metadata.get(
            "transcript_by", ""
        )
        document_data["transcript_source"] = os.path.dirname(file_path)

        # Extract language from file name
        lang_code = self.extract_language_code(file_path)
        if lang_code:
            document_data["language"] = lang_code

        return document_data

    def extract_language_code(self, file_path: str) -> str:
        # Extract the language code from the file name
        match = re.search(r"\.([a-z]{2})\.md$", file_path)
        if match:
            return match.group(1)
        return "en"  # Default to English if no language code is found

    def get_url(self, file_path: str, metadata: Dict[str, Any]) -> str:
        lang_code = self.extract_language_code(file_path)

        # Remove the file extension
        path_without_extension = os.path.splitext(file_path)[0]

        # Remove the language code suffix if present
        path_without_lang = re.sub(r"\.[a-z]{2}$", "", path_without_extension)

        if lang_code != "en":
            # For non-English content, add the language code at the beginning of the path
            return urljoin(str(self.config.domain), f"{lang_code}/{path_without_lang}")
        else:
            # For English content, use the path as is
            return urljoin(str(self.config.domain), path_without_lang)
