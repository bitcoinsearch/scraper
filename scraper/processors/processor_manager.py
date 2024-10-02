from typing import List
from scraper.models import ScrapedDocument
from .base_processor import BaseProcessor


class ProcessorManager:
    def __init__(self, processors: List[BaseProcessor]):
        self.processors = processors

    async def process_document(self, document: ScrapedDocument) -> ScrapedDocument:
        for processor in self.processors:
            document = await processor.process(document)
        return document
