import os
from datetime import date, datetime
import re
from git import Repo
from loguru import logger
from typing import List, Dict, Any, Set, Type

import yaml

from scraper.models import ScrapedDocument
from scraper.config import settings
from scraper.utils import slugify, strip_emails
from scraper.registry import scraper_registry
from .base import BaseScraper


@scraper_registry.register("bolts")
class GithubScraper(BaseScraper):
    FRONT_MATTER_START = FRONT_MATTER_END = "---"
    DEFAULT_EXCLUDED_FILES = {"README.md", "CONTRIBUTING.md", "LICENSE.md"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repo_path = os.path.join(settings.DATA_DIR, slugify(self.config.name))
        self._excluded_files = self.DEFAULT_EXCLUDED_FILES.copy()
        self.document_class: Type[ScrapedDocument] = ScrapedDocument
        self.test_resources = self.config.test_resources

    @property
    def excluded_files(self) -> Set[str]:
        return self._excluded_files

    def add_excluded_files(self, files: List[str]):
        self._excluded_files.update(files)

    async def scrape(self):
        metadata = await self.get_metadata(self.config)
        last_commit_hash = metadata.last_commit_hash

        repo = self.clone_or_pull_repo()

        # Handle test mode vs full mode
        if self.test_resources:
            logger.info(f"Running in test mode with resources: {self.test_resources}")
            files_to_process = self.test_resources
        else:
            logger.info("Running in full mode")
            files_to_process = self.get_changed_files(repo, last_commit_hash)

        documents_indexed = await self.process_files(repo, files_to_process)

        # Only update metadata in full mode
        if not self.test_resources:
            metadata.last_commit_hash = repo.head.commit.hexsha
            metadata.files_processed = len(files_to_process)
            metadata.documents_indexed = documents_indexed
            await self.update_metadata(metadata)

    def get_changed_files(self, repo: Repo, last_commit_hash: str) -> List[str]:
        if not last_commit_hash:
            # If no previous commit hash, consider all files as changed
            return [item.path for item in repo.tree().traverse() if item.type == "blob"]

        current_commit = repo.head.commit
        previous_commit = repo.commit(last_commit_hash)

        diff_index = previous_commit.diff(current_commit)

        changed_files = []
        for diff_item in diff_index:
            if diff_item.a_path:
                changed_files.append(diff_item.a_path)
            if diff_item.b_path and diff_item.b_path != diff_item.a_path:
                changed_files.append(diff_item.b_path)

        return list(set(changed_files))

    def clone_or_pull_repo(self) -> Repo:
        if os.path.exists(self.repo_path):
            logger.info(f"Updating existing repo at path: {self.repo_path}")
            repo = Repo(self.repo_path)
            origin = repo.remotes.origin
            origin.pull()
        else:
            logger.info(f"Cloning repo to path: {self.repo_path}")
            repo = Repo.clone_from(self.config.url, self.repo_path)
        return repo

    async def process_files(self, repo: Repo, files: List[str]) -> int:
        """Process a list of files from the repository."""
        processed_documents = 0
        for file_path in files:
            if self.is_relevant_file(file_path):
                logger.info(f"Processing file: {file_path}")
                document = self.parse_file(repo, file_path)
                if document:
                    await self.process_and_index_document(document)
                    processed_documents += 1
                else:
                    logger.warning(f"Failed to parse file: {file_path}")
        return processed_documents

    def is_relevant_file(self, file_path: str) -> bool:
        file_name = os.path.basename(file_path)

        # Check for hidden files
        if file_name.startswith("."):
            return False

        # Check against excluded files
        if file_name in self.excluded_files:
            return False

        # Check if the file is in the specified directories (if any)
        if self.config.directories:
            if not any(file_path.startswith(dir) for dir in self.config.directories):
                return False

        # Check file type
        return self.is_valid_file_type(file_path)

    def is_valid_file_type(self, file_path: str) -> bool:
        """
        Check if the file is of a valid type.
        This method can be overridden in subclasses to customize file type checking.
        """
        return file_path.endswith(".md")

    def parse_markdown(self, text: str) -> tuple[Dict[str, Any], str]:
        """Parses a markdown text to extract metadata and the document body"""
        # Remove content between {% %}
        text = re.sub(r"{%.*?%}", "", text, flags=re.MULTILINE | re.DOTALL)

        start_delimiter = re.escape(self.FRONT_MATTER_START)
        end_delimiter = re.escape(self.FRONT_MATTER_END)
        pattern = re.compile(
            rf"^{start_delimiter}\s*$(.*?)^{end_delimiter}\s*$",
            re.DOTALL | re.MULTILINE,
        )
        match = pattern.search(text)

        if match:
            # Extract the front matter and the body
            front_matter = match.group(1).strip()
            body = text[match.end() :].strip()

            # Try YAML parsing first
            try:
                metadata = yaml.safe_load(front_matter)
                if not isinstance(metadata, dict):
                    raise ValueError("YAML content is not a dictionary")
            except (yaml.YAMLError, ValueError):
                # If YAML parsing fails, fall back to BIP-style parsing
                metadata = self._parse_bip_style_content(front_matter)
        else:
            # If no front matter is found, treat the entire text as body
            metadata = {}
            body = text.strip()

        return metadata, body

    def _parse_bip_style_content(self, content: str) -> Dict[str, Any]:
        metadata = {}
        current_key = None
        for line in content.split("\n"):
            line = line.strip()
            if ":" in line:
                # If the line contains a colon, it's a new key-value pair
                key, value = line.split(":", 1)
                current_key = key.strip()
                # Initialize as a list to handle multi-line fields
                metadata[current_key] = [value.strip()]
            elif current_key:
                # Handle multi-line values by appending to the current key
                metadata[current_key].append(line)

        # Convert single-entry lists to strings for consistency
        for key in metadata:
            if len(metadata[key]) == 1 and key != "Author":
                metadata[key] = metadata[key][0]

        return metadata

    def parse_file(self, repo: Repo, file_path: str) -> ScrapedDocument:
        try:
            with open(
                os.path.join(repo.working_dir, file_path), "r", encoding="utf-8"
            ) as file:
                content = file.read()
            metadata, body = self.parse_markdown(content)

            document_data = {
                "id": self.generate_id(file_path),
                "title": self.get_title(metadata, body),
                "body": body,
                "body_formatted": body,
                "summary": metadata.get("summary", None),
                "body_type": self.get_body_type(file_path),
                "domain": str(self.config.domain),
                "created_at": self.get_created_at(metadata),
                "url": self.get_url(file_path, metadata),
                "type": self.determine_document_type(file_path),
                "language": self.get_language(metadata),
                "authors": self.get_authors(metadata),
                "tags": metadata.get("tags", None),
            }

            document_data = self.customize_document(document_data, file_path, metadata)

            return self.document_class(**document_data)
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return None

    def customize_document(
        self, document_data: Dict[str, Any], file_path: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        This method allows subclasses to add or modify fields in the document data.
        Override this method in subclasses to add custom fields.
        """
        return document_data

    def generate_id(self, file_path: str) -> str:
        # Override this method to customize ID generation
        file_name = os.path.basename(file_path)
        name_without_extension = os.path.splitext(file_name)[0]
        return f"{self.config.name.lower()}-{slugify(name_without_extension)}"

    def get_title(self, metadata: Dict[str, Any], body: str) -> str:
        # First, check if there's a title in the metadata
        if "title" in metadata:
            return metadata["title"]
        if "Title" in metadata:
            return metadata["Title"]

        # If not, look for the first header in the markdown body
        header_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        if header_match:
            return header_match.group(1).strip()

        # If no title is found, return a default string
        return "Untitled"

    def get_created_at(self, metadata: Dict[str, Any]) -> str:
        # Handle 'date' field if it's a string
        if isinstance(metadata.get("date"), str):
            return datetime.strptime(metadata["date"], "%Y-%m-%d").strftime("%Y-%m-%d")

        # Handle 'Created' field if it's a string or a date
        created = metadata.get("Created")
        if isinstance(created, str):
            return created  # Assume the string is already in the desired format
        elif isinstance(created, date):
            # Format the date as 'YYYY-MM-DD'
            return created.strftime("%Y-%m-%d")

        # If no valid date found, return None
        return None

    def get_language(self, metadata: Dict[str, Any]) -> str:
        # Override this method to customize language extraction
        return metadata.get("lang", "en")

    def get_body_type(self, file_path: str) -> str:
        # Override this method to customize body type extraction
        file_extension = os.path.splitext(file_path)[1]
        return "mediawiki" if file_extension == ".mediawiki" else "markdown"

    def get_authors(self, metadata: Dict[str, Any]) -> List[str]:
        # Override this method to customize author extraction
        authors = metadata.get("authors") or metadata.get("Author")
        if not authors:
            return None
        # Ensure authors is a list, and apply strip_emails to each item
        if isinstance(authors, str):
            authors = [authors]  # Convert single string to list
        # Apply strip_emails to all author entries
        return [strip_emails(author) for author in authors]

    def get_url(self, file_path: str, metadata: Dict[str, Any]) -> str:
        # Override this method to customize URL construction
        base_url = f"{self.config.domain}"

        # Use permalink if available in metadata
        if "permalink" in metadata:
            return f"{base_url}{metadata['permalink']}"

        # Check if it's a GitHub repository
        if base_url.startswith("https://github.com/"):
            # For GitHub repos, include '/blob/master' in the URL
            return f"{base_url}/blob/master/{file_path}"

        # Fall back to constructing URL from file path
        return f"{base_url}/{file_path.replace('.md', '')}"

    def determine_document_type(self, file_path: str) -> str:
        # Override this method to customize document type determination
        if not self.config.directories:
            return self.config.type or None  # Use the source-level type if available

        for directory, content_type in self.config.directories.items():
            if file_path.startswith(directory):
                return content_type

        return None  # Default type if no match is found
