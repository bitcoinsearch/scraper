from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from scraper.models.documents import ScrapedDocument


class Review(BaseModel):
    """Represents a formal code review on a pull request"""

    id: int = Field(description="Unique identifier for the review")
    author: str = Field(description="Username of the reviewer")
    commit_id: str = Field(
        description="The SHA of the commit to which the review applies"
    )
    submitted_at: str = Field(description="When the review was submitted")
    body: str = Field(description="The review's comment text")


class ThreadComment(BaseModel):
    """Represents a comment in a review thread"""

    id: int = Field(description="Unique identifier for the comment")
    author: str = Field(description="Username of the comment author")
    created_at: str = Field(description="When the comment was created")
    updated_at: str = Field(description="When the comment was last updated")
    body: str = Field(description="The text of the comment")
    pull_request_review_id: Optional[int] = Field(
        None, description="ID of the associated review"
    )


class ReviewThread(BaseModel):
    """Represents a discussion thread on a specific code section"""

    pull_request_review_id: Optional[int] = Field(
        None, description="The ID of the pull request review that initiated this thread"
    )
    path: str = Field(
        description="The relative path of the file to which the thread applies"
    )
    diff_hunk: str = Field(
        description="The diff of the line that the review thread refers to"
    )
    commit_id: str = Field(
        description="The SHA of the commit to which the review thread applies"
    )
    original_commit_id: str = Field(
        description="The SHA of the original commit to which the review thread applies"
    )
    position: Optional[int] = Field(
        None,
        description="The line index in the diff to which the comment applies. This field is closing down; use `line` instead",
    )
    original_position: Optional[int] = Field(
        None,
        description="The index of the original line in the diff to which the comment applies. This field is closing down; use `original_line` instead.",
    )
    line: Optional[int] = Field(
        None,
        description="The line of the blob to which the review thread applies. The last line of the range for a multi-line comment",
    )
    original_line: Optional[int] = Field(
        None,
        description="The original line of the blob to which the review thread applies. The last line of the range for a multi-line comment",
    )
    start_line: Optional[int] = Field(
        None, description="The first line of the range for a multi-line comment"
    )
    original_start_line: Optional[int] = Field(
        None,
        description="The original first line of the range for a multi-line comment",
    )
    comments: List[ThreadComment] = Field(
        default_factory=list, description="Comments in this thread"
    )


class Comment(BaseModel):
    """Represents a general comment on the issue/PR"""

    id: int = Field(description="Unique identifier for the comment")
    author: str = Field(description="Username of the comment author")
    created_at: str = Field(description="When the comment was created")
    updated_at: str = Field(description="When the comment was last updated")
    body: str = Field(description="The text of the comment")


class GitHubDocument(ScrapedDocument):
    """Represents a GitHub Issue or Pull Request document with all its associated data"""

    type: Literal["issue", "pull"] = Field(
        description="Document type: 'issue' or 'pull'"
    )
    number: str = Field(description="Issue or PR number")
    body: str = Field(description="Issue/PR description")
    body_type: Literal["markdown"] = Field(
        "markdown", description="Content format type"
    )
    created_at: str = Field(description="When the issue/PR was created")
    updated_at: str = Field(description="When the issue/PR was last updated")
    closed_at: Optional[str] = Field(description="When the issue/PR was closed")
    merged_at: Optional[str] = Field(description="When the PR was merged")
    state: Literal["open", "merged", "closed", "draft"] = Field(
        description="Current state"
    )
    labels: List[str] = Field(default_factory=list, description="Issue/PR labels")

    # Optional PR-specific fields
    head_sha: Optional[str] = Field(
        default=None, description="SHA of the PR head commit"
    )
    draft: Optional[bool] = Field(
        default=False, description="Whether the PR is a draft"
    )
    reviews: Optional[List[Review]] = Field(
        default=None, description="Formal code reviews (PR only)"
    )
    review_threads: Optional[List[ReviewThread]] = Field(
        default=None, description="Code review discussion threads (PR only)"
    )

    # Common fields
    comments: List[Comment] = Field(
        default_factory=list, description="General comments"
    )
