from abc import ABC, abstractmethod
from typing import Dict, Any

from scraper.models import ScrapedDocument


class BaseProcessor(ABC):
    @abstractmethod
    async def process(self, document: ScrapedDocument) -> ScrapedDocument:
        """
        Process a single document.

        Args:
            document (ScrapedDocument): The document to process.

        Returns:
            Dict[ScrapedDocument]: The processed document.
        """
        pass
