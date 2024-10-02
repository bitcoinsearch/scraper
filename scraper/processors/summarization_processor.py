from scraper.models import ScrapedDocument
from .base_processor import BaseProcessor
from scraper.registry import processor_registry


@processor_registry.register("summarization")
class SummarizationProcessor(BaseProcessor):
    async def process(self, document: ScrapedDocument) -> ScrapedDocument:
        # Placeholder logic - replace with actual summary generation
        if document.body:
            document.summary = document.body[:200] + "..."
        return document
