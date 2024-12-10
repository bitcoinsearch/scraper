import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from scraper.registry import scraper_registry
from scraper.scrapers.github import GithubScraper
from scraper.models.github_metadata import (
    GitHubDocument,
    Review,
    ReviewThread,
    ThreadComment,
    Comment,
)


@scraper_registry.register(
    "github-metadata-bitcoin-bips",
    "github-metadata-bitcoin-bitcoin",
    "github-metadata-bitcoin-core-secp256k1",
    "github-metadata-bitcoin-core-gui",
)
class GitHubMetadataScraper(GithubScraper):
    """
    Specialized scraper for GitHub Issues and Pull Requests data stored in JSON files.
    Transforms the raw GitHub API backup data into our normalized document format.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_class = GitHubDocument

    def is_valid_file_type(self, file_path: str) -> bool:
        """Override to check for JSON files instead of markdown."""
        return file_path.endswith(".json")

    def parse_file(self, repo, file_path: str) -> Optional[GitHubDocument]:
        """
        Parse a JSON file containing GitHub issue/PR data.

        Args:
            repo: The Git repository object
            file_path: Path to the JSON file within the repository

        Returns:
            GitHubDocument: The parsed document or None if parsing fails
        """
        try:
            # Read the JSON file
            with open(Path(repo.working_dir) / file_path, "r", encoding="utf-8") as f:
                json_content = json.load(f)

            # Process the JSON content
            document_data = self.map_json_to_document(json_content, file_path)

            # Add common fields
            document_data.update(
                {
                    "id": self.generate_id(file_path),
                    "domain": str(self.config.domain),
                    "url": self.get_url(file_path, document_data),
                }
            )

            return self.document_class(**document_data)

        except Exception as e:
            logger.error(f"Error parsing JSON file {file_path}: {e}")
            logger.exception("Full traceback:")
            return None

    def map_json_to_document(
        self, json_content: Dict[str, Any], file_path: str
    ) -> Dict[str, Any]:
        """Transform GitHub JSON data into our document format"""
        try:
            content_type = json_content["type"]
            if content_type not in ["issue", "pull"]:
                raise ValueError(f"Unknown content type: {content_type}")

            data = json_content[content_type]

            # Map base fields common to both issues and PRs
            document_data = {
                "type": content_type,
                "number": str(data["number"]),
                "title": data["title"],
                "authors": [data["user"]["login"]],
                "body": data.get("body", ""),
                "body_type": "markdown",
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "closed_at": data.get("closed_at"),
                "merged_at": data.get("merged_at"),
                "state": self._determine_state(data, content_type),
                "labels": [label["name"] for label in data["labels"]],
                "comments": self._extract_comments(json_content),
            }

            # Add PR-specific fields if this is a pull request
            if content_type == "pull":
                document_data.update(
                    {
                        "head_sha": data["head"]["sha"],
                        "draft": data.get("draft", False),
                        "reviews": self._extract_reviews(json_content),
                        "review_threads": self._extract_review_threads(json_content),
                    }
                )

            return document_data

        except Exception as e:
            logger.error(f"Error mapping data from {file_path}: {e}")
            raise

    def _determine_state(self, data: Dict[str, Any], content_type: str) -> str:
        """Determine the state based on content type and data"""
        if content_type == "pull":
            if data.get("merged_at"):
                return "merged"

        return data["state"]  # "open" or "closed"

    def _extract_reviews(self, json_content: Dict[str, Any]) -> List[Review]:
        """Extract formal reviews from events"""
        reviews = []
        for event in json_content["events"]:
            if event.get("event") == "reviewed":
                try:
                    reviews.append(
                        Review(
                            id=int(event["id"]),
                            author=event["user"]["login"],
                            commit_id=event["commit_id"],
                            submitted_at=event["submitted_at"],
                            body=event.get("body", ""),
                        )
                    )
                except Exception as e:
                    logger.warning(f"Skipping invalid review: {e}")
        return reviews

    def _extract_review_threads(
        self, json_content: Dict[str, Any]
    ) -> List[ReviewThread]:
        """Extract review threads from comments"""
        # Group comments by their thread attributes
        threads: Dict[str, List[Dict[str, Any]]] = {}

        # Comments array contains only review thread comments
        for comment in json_content["comments"]:
            thread_key = f"{comment['path']}:{comment.get('position')}:{comment.get('original_position')}"

            if thread_key not in threads:
                threads[thread_key] = []
            threads[thread_key].append(comment)

        # Convert grouped comments to ReviewThread objects
        review_threads = []
        for thread_comments in threads.values():
            if not thread_comments:
                continue

            # Use the first comment for thread-level attributes
            first_comment = thread_comments[0]
            try:
                thread = ReviewThread(
                    pull_request_review_id=first_comment.get("pull_request_review_id"),
                    path=first_comment["path"],
                    diff_hunk=first_comment.get("diff_hunk", ""),
                    commit_id=first_comment["commit_id"],
                    original_commit_id=first_comment["original_commit_id"],
                    position=first_comment.get("position"),
                    original_position=first_comment.get("original_position"),
                    line=first_comment.get("line"),
                    original_line=first_comment.get("original_line"),
                    start_line=first_comment.get("start_line"),
                    original_start_line=first_comment.get("original_start_line"),
                    comments=[
                        self._convert_to_thread_comment(c) for c in thread_comments
                    ],
                )
                review_threads.append(thread)
            except Exception as e:
                logger.warning(f"Skipping invalid review thread: {e}")

        return review_threads

    def _convert_to_thread_comment(self, comment: Dict[str, Any]) -> ThreadComment:
        """Convert a raw comment dict to a ThreadComment object"""
        return ThreadComment(
            id=int(comment["id"]),
            author=comment["user"]["login"],
            created_at=comment["created_at"],
            updated_at=comment["updated_at"],
            body=comment["body"],
            pull_request_review_id=comment.get("pull_request_review_id"),
        )

    def _extract_comments(self, json_content: Dict[str, Any]) -> List[Comment]:
        """Extract general comments from events array where event type is 'commented'"""
        comments = []
        for event in json_content["events"]:
            if event.get("event") != "commented":
                continue

            try:
                comments.append(
                    Comment(
                        id=int(event["id"]),
                        author=event["actor"]["login"],
                        created_at=event["created_at"],
                        updated_at=event["updated_at"],
                        body=event["body"],
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping invalid comment: {e}")

        return comments

    def get_url(self, file_path: str, metadata: Dict[str, Any]) -> str:
        """Generate the GitHub web URL for the issue/PR"""
        base_url = self.config.domain
        item_type = metadata.get("type")
        number = metadata.get("number")

        if not all([base_url, item_type, number]):
            raise ValueError("Missing required fields: domain, type, or number")

        if item_type == "issue":
            return f"{base_url}/issues/{number}"
        elif item_type == "pull":
            return f"{base_url}/pull/{number}"
        else:
            raise ValueError(f"Invalid type: {item_type}. Must be 'issue' or 'pull'")
