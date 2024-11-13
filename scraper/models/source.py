from typing import Dict, List, Optional
from pydantic import BaseModel, HttpUrl


class AnalyzerConfig(BaseModel):
    """Configuration for the LLM analyzer"""

    index_url: HttpUrl
    resource_url: HttpUrl


class SourceConfig(BaseModel):
    """Configuration for a source to be scraped"""

    name: str
    domain: HttpUrl
    url: HttpUrl
    filter_by_author: Optional[bool] = False
    default_author: Optional[str] = None
    directories: Optional[Dict[str, str]] = None
    index_name: Optional[str] = None
    type: Optional[str] = None
    test_resources: Optional[List[str]] = []
    processors: List[str] = []
    analyzer_config: Optional[AnalyzerConfig] = None


__all__ = ["SourceConfig", "AnalyzerConfig"]
