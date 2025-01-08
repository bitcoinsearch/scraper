from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class OriginalContent(BaseModel):
    """Represents the original content before markdown conversion"""

    format: str = Field(
        description="Original format of the content (e.g., 'mediawiki', 'html')"
    )
    body: str = Field(description="Original content in its native format")


class ScrapedDocument(BaseModel):
    """
    Represents a document scraped from a source.

    This model defines the structure and types of data that should be present
    in every scraped document. It uses Pydantic for data validation and serialization.
    """

    id: str = Field(description="Unique identifier for the document")
    title: str = Field(description="Title of the document")
    body: str = Field(description="Main content of the document in markdown format")
    original: Optional[OriginalContent] = Field(
        default=None, description="Original content before markdown conversion"
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


class BitcoinTranscriptDocument(ScrapedDocument):
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


class PRReviewClubDocument(ScrapedDocument):
    number: Optional[int] = Field(
        default_factory=None,
        description="Bitcoin Core PR number associated with the meeting",
    )
    host: Optional[str] = Field(
        default=None, description="The person hosting the meeting"
    )


class StackExchangeDocument(ScrapedDocument):
    accepted_answer_id: Optional[str] = Field(
        default=None, description="ID of the accepted answer"
    )


class RunStats(BaseModel):
    """Statistics for a single scraper run"""

    resources_to_process: Optional[int] = Field(
        default=None, description="Number of available resources to process in this run"
    )
    documents_indexed: Optional[int] = Field(
        default=None, description="Number of documents successfully indexed in this run"
    )


class ScraperRunDocument(BaseModel):
    """Represents a single run of a scraper with its statistics"""

    scraper: str = Field(description="Name of the scraper")
    source: str = Field(description="Name of the source")
    domain: str = Field(description="Domain being scraped")
    started_at: str = Field(description="When this run started")
    finished_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When this run finished",
    )
    type: str = Field(
        default="scraper_run",
        description="Type of the document, always 'scraper_run' for run documents",
    )
    last_commit_hash: Optional[str] = Field(
        default=None, description="Last commit hash for Git-based scrapers"
    )
    success: bool = Field(description="Whether the run completed successfully")
    error_message: Optional[str] = Field(
        default=None, description="Error message if the run failed"
    )
    stats: RunStats = Field(description="Statistics for this run")
