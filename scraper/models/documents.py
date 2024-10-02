from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ScrapedDocument(BaseModel):
    """
    Represents a document scraped from a source.

    This model defines the structure and types of data that should be present
    in every scraped document. It uses Pydantic for data validation and serialization.
    """

    id: str = Field(description="Unique identifier for the document")
    title: str = Field(description="Title of the document")
    body: str = Field(description="Main content of the document")
    body_formatted: Optional[str] = Field(
        default=None, description="Formatted content of the document"
    )
    body_type: str = Field(
        description="Type of the body content (e.g., 'markdown', 'mediawiki')"
    )
    summary: Optional[str] = Field(default=None, description="Summary of the document")
    summary_vector_embeddings: Optional[List[float]] = Field(
        default=None, description="Vector embeddings of the summary"
    )
    domain: str = Field(description="Domain from which the document was scraped")
    indexed_at: str = Field(
        default_factory=datetime.now().isoformat,
        description="Timestamp of when the document was indexed",
    )
    created_at: Optional[str] = Field(
        default=None, description="Timestamp of when the document was created"
    )
    url: str = Field(description="URL of the original document")
    thread_url: str = Field(
        default=None, description="URL of the thread that contains the document"
    )
    type: Optional[str] = Field(default=None, description="Type of the document")
    language: Optional[str] = Field(
        default=None, description="Language of the document"
    )
    tags: Optional[List[str]] = Field(
        default=None, description="List of tags associated with the document"
    )
    authors: Optional[List[str]] = Field(
        default=None, description="List of authors of the document"
    )
    test_document: Optional[bool] = Field(
        # TODO: remove hardcoded value
        default=True,
        description="Flag indicating if this is a test document",
    )


class BitcoinTranscriptDocument(ScrapedDocument):
    tags: List[str] = Field(
        default_factory=list, description="Tags associated with the transcript"
    )
    media: Optional[str] = Field(
        default=None, description="Media associated with the transcript"
    )
    transcript_by: Optional[str] = Field(
        default=None, description="Person or entity who transcribed the content"
    )
    needs_review: bool = Field(
        default=False, description="Flag indicating if the transcript needs review"
    )
    transcript_source: str = Field(description="Source of the transcript")


class MetadataDocument(BaseModel):
    """
    Represents metadata about a scraping operation for a specific domain.

    This model defines the structure and types of data that should be present
    in every metadata document. It uses Pydantic for data validation and serialization.
    """

    id: str = Field(description="Unique identifier for the document")
    domain: str = Field(..., description="Domain for which this metadata applies")
    updated_at: str = Field(
        default_factory=datetime.now().isoformat,
        description="Timestamp of the last scrape operation",
    )
    last_commit_hash: Optional[str] = Field(
        None, description="Hash of the last processed commit (for Git repositories)"
    )
    files_processed: Optional[int] = Field(
        default=None, description="Number of files processed in the last scrape"
    )
    documents_indexed: Optional[int] = Field(
        default=None,
        description="Number of documents successfully indexed in the last scrape",
    )
    type: str = Field(
        default="scrape_metadata",
        description="Type of the document, always 'scrape_metadata' for metadata",
    )
    test_document: bool = Field(
        # TODO: remove hardcoded value
        default=True,
        description="Flag indicating if this is a test metadata document",
    )
