from typing import Optional
from pydantic import BaseModel, Field


class SelectorConfig(BaseModel):
    """Configuration for a CSS selector"""

    selector: str = Field(..., description="CSS selector string")
    attribute: Optional[str] = Field(
        None, description="HTML attribute to extract (e.g., 'href', 'src')"
    )
    multiple: bool = Field(
        default=None, description="Whether to expect multiple elements"
    )
    pattern: Optional[str] = Field(None, description="Regex pattern to match/extract")


class ItemConfig(BaseModel):
    """Configuration for items (both resource listings and content items)"""

    item_selector: SelectorConfig = Field(
        ..., description="Selector to find individual items"
    )
    author: Optional[SelectorConfig] = None
    date: Optional[SelectorConfig] = None
    content: Optional[SelectorConfig] = None
    title: Optional[SelectorConfig] = None
    url: Optional[SelectorConfig] = None


class PageConfig(BaseModel):
    """Configuration for any page type (index or resource)"""

    items: ItemConfig
    next_page: Optional[SelectorConfig] = None
    url_pattern: Optional[str] = None


class ScrapingConfig(BaseModel):
    """Complete scraping configuration"""

    index_page: PageConfig
    resource_page: PageConfig
