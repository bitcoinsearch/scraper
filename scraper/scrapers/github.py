import os
from datetime import date, datetime
import re
from urllib.parse import urljoin
from git import Repo
from loguru import logger
from typing import List, Dict, Any, Optional, Set, Type

import yaml

from scraper.models import ScrapedDocument, RunStats
from scraper.config import settings
from scraper.scrapers.utils import parse_standard_date_formats
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
        """
        Main scraping method for GitHub repositories.
        Uses last successful run's commit hash to determine what files to process.
        """
        # Get last successful run for commit hash
        last_run = await self.get_last_successful_run()
        last_commit_hash = last_run.last_commit_hash if last_run else None

        repo = self.clone_or_pull_repo()
        # If checkout_commit is specified, use that specific commit state
        if self.config.checkout_commit:
            try:
                repo.git.checkout(self.config.checkout_commit)
            except Exception as e:
                logger.error(
                    f"Failed to checkout commit {self.config.checkout_commit}: {e}"
                )
                raise

        self.current_commit_hash = repo.head.commit.hexsha

        # Handle test mode vs full mode
        if self.test_resources:
            logger.info(f"Running in test mode with resources: {self.test_resources}")
            files_to_process = self.test_resources
        else:
            logger.info(
                f"Running in full mode: {last_commit_hash} -> {self.current_commit_hash}"
            )
            files_to_process = self.get_changed_files(repo, last_commit_hash)

        # Process files
        self.resources_to_process = len(files_to_process)
        await self.process_files(repo, files_to_process)

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

            # Reset any changes and checkout main branch before pulling
            repo.git.reset("--hard")

            # Get default branch name (usually main or master)
            default_branch = repo.git.symbolic_ref("refs/remotes/origin/HEAD").split(
                "/"
            )[-1]
            repo.git.checkout(default_branch)

            # Now pull the latest changes
            origin = repo.remotes.origin
            origin.pull()
        else:
            logger.info(f"Cloning repo to path: {self.repo_path}")
            repo = Repo.clone_from(self.config.url, self.repo_path)
        return repo

    async def process_files(self, repo: Repo, files: List[str]) -> int:
        """Process a list of files from the repository."""
        for file_path in files:
            if self.is_relevant_file(file_path):
                logger.info(f"Processing file: {file_path}")
                document = self.parse_file(repo, file_path)
                if document:
                    await self.process_and_index_document(document)
                else:
                    logger.warning(f"Failed to parse file: {file_path}")

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
                "original": None,  # TODO handle .mediawiki
                "summary": metadata.get("summary", None),
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
        """
        Override this method in subclasses to customize ID generation.
        """
        # Since file_path is relative (e.g. 'tabconf/2022/file.zh.md'),
        # we can safely use directory structure in ID generation
        dir_path = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        # Keep language suffix (e.g. .zh) but remove final extension (.md)
        name_without_extension = os.path.splitext(file_name)[0]
        return f"{self.config.name.lower()}-{slugify(dir_path)}-{slugify(name_without_extension)}"

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

    def get_created_at(self, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract and normalize creation date from document metadata.

        Attempts to parse date from multiple common metadata fields and formats.
        Returns ISO formatted date string (YYYY-MM-DD) or None if no valid date found.

        Args:
            metadata: Document metadata dictionary

        Returns:
            Optional[str]: ISO formatted date string or None
        """
        # List of common metadata field names for dates
        date_fields = [
            "date",
            "created",
            "created_at",
            "published",
            "published_at",
            "timestamp",
        ]

        for field in date_fields:
            value = metadata.get(field) or metadata.get(field.title())
            if not value:
                continue

            # Handle datetime/date objects
            if isinstance(value, (datetime, date)):
                return value.strftime("%Y-%m-%d")

            # Handle string dates
            if isinstance(value, str):
                # Try standard date formats using utility function
                parsed_date = parse_standard_date_formats(value)
                if parsed_date:
                    # Convert full ISO timestamp to date-only format if needed
                    if "T" in parsed_date:
                        return parsed_date.split("T")[0]
                    return parsed_date

        # No valid date found
        return None

    def get_language(self, metadata: Dict[str, Any]) -> str:
        # Override this method to customize language extraction
        return metadata.get("lang", "en")

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
        # Use permalink if available
        if "permalink" in metadata:
            return urljoin(str(self.config.domain), metadata["permalink"])

        # Special handling for GitHub repositories
        if self.config.domain.host == "github.com":
            # For GitHub repos, include '/blob/master' in the URL
            github_path = f"blob/master/{file_path}"
            return urljoin(str(self.config.domain), github_path)

        # Fall back to constructing URL from file path
        return urljoin(str(self.config.domain), f"{file_path.replace('.md', '')}")

    def determine_document_type(self, file_path: str) -> str:
        # Override this method to customize document type determination
        if not self.config.directories:
            return self.config.type or None  # Use the source-level type if available

        for directory, content_type in self.config.directories.items():
            if file_path.startswith(directory):
                return content_type

        return None  # Default type if no match is found

    def analyze_metadata(self, store_all_values: bool = False) -> dict:
        """
        Analyze metadata fields in all markdown files of the repository.

        Args:
            store_all_values: If True, store all unique values for each field instead of examples

        Returns:
            dict: Analysis results including field frequencies, types, and values/examples
        """
        # Clone or update repository
        repo = self.clone_or_pull_repo()

        # Initialize analysis data structure
        analysis = {"total_documents": 0, "metadata_fields": {}}

        # Analyze all markdown files
        for item in repo.tree().traverse():
            if item.type != "blob" or not self.is_relevant_file(item.path):
                continue

            try:
                # Read and parse file
                with open(
                    os.path.join(repo.working_dir, item.path), "r", encoding="utf-8"
                ) as f:
                    content = f.read()
                metadata, _ = self.parse_markdown(content)

                if metadata:
                    analysis["total_documents"] += 1
                    self._analyze_metadata_fields(
                        metadata, analysis["metadata_fields"], store_all_values
                    )

            except Exception as e:
                logger.warning(f"Error analyzing file {item.path}: {e}")
                logger.error("Full traceback:", exc_info=True)
                continue

        # Convert sets to lists for JSON serialization at the end
        self._prepare_for_json(analysis["metadata_fields"])

        return analysis

    def _analyze_metadata_fields(
        self, metadata: dict, field_registry: dict, store_all_values: bool
    ):
        """
        Analyze metadata fields from a single document and update the registry.

        Args:
            metadata: Dict of metadata from a document
            field_registry: Registry to update with findings
            store_all_values: If True, store all unique values instead of examples
        """
        for field, value in metadata.items():
            if field not in field_registry:
                field_registry[field] = {
                    "count": 0,
                    "types": set(),
                    "values"
                    if store_all_values
                    else "examples": set()
                    if store_all_values
                    else [],
                }

            # Update count
            field_registry[field]["count"] += 1

            # Track value type
            value_type = self._get_value_type(value)
            field_registry[field]["types"].add(value_type)

            # Convert date/datetime to string for JSON serialization
            if isinstance(value, (date, datetime)):
                value = value.isoformat()

            # Handle value storage based on mode
            if store_all_values:
                # For all values mode, use a set to track unique values
                if isinstance(value, (list, tuple)):
                    # For arrays, convert to tuple to make it hashable
                    field_registry[field]["values"].add(str(value))
                else:
                    field_registry[field]["values"].add(value)
            else:
                # For examples mode, keep up to 3 examples
                if len(field_registry[field]["examples"]) < 3:
                    if value not in field_registry[field]["examples"]:
                        field_registry[field]["examples"].append(value)

    def _prepare_for_json(self, field_registry: dict):
        """Convert sets to lists for JSON serialization."""
        for field in field_registry:
            field_registry[field]["types"] = list(field_registry[field]["types"])

            if "values" in field_registry[field]:
                field_registry[field]["values"] = list(field_registry[field]["values"])

    def _get_value_type(self, value) -> str:
        """
        Determine the type of a metadata value.

        Returns:
            str: Name of the type ("string", "array", "number", "boolean", "null")
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, (list, tuple)):
            return "array"
        elif isinstance(value, dict):
            return "object"
        elif isinstance(value, datetime):
            return "datetime"
        else:
            return "string"
