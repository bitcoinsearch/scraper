import re
import unicodedata
from typing import Tuple

from markdownify import markdownify as md


def slugify(value: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    - Normalize to ASCII
    - Replace spaces and underscores with hyphens
    - Remove characters that aren't alphanumerics, underscores, or hyphens
    - Convert to lowercase
    - Strip leading and trailing hyphens
    """
    # Normalize to ASCII
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )

    # Replace spaces and underscores with hyphens, remove invalid characters
    value = re.sub(r"[_\s]+", "-", value)  # Replace spaces and underscores
    value = re.sub(r"[^\w-]", "", value)  # Remove invalid characters

    # Convert to lowercase and strip leading/trailing hyphens
    return value.strip("-").lower()


def strip_emails(text: str) -> str:
    """Remove email addresses from the given text."""
    return re.sub(r"<.*?>", "", text).strip()


def html_to_markdown(html_content: str) -> Tuple[str, dict]:
    """
    Convert HTML content to markdown format.

    Args:
        html_content: The HTML content to convert

    Returns:
        Tuple containing:
        - The converted markdown content
        - Original content object with format and body
    """
    markdown_content = md(html_content)
    original = {"format": "html", "body": html_content}

    return markdown_content, original
