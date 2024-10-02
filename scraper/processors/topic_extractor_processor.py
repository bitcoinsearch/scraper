import json
from typing import List

from scraper.models import ScrapedDocument
from .base_processor import BaseProcessor
from scraper.registry import processor_registry


@processor_registry.register("topic_extractor")
class TopicExtractorProcessor(BaseProcessor):
    def __init__(self):
        self.topics_list = self.load_topics()

    def load_topics(self) -> List[str]:
        with open("scraper/processors/topics_list.json", "r") as f:
            return json.load(f)["topics"]

    async def process(self, document: ScrapedDocument) -> ScrapedDocument:
        # Placeholder logic - replace with actual topic extraction
        if document.body:
            document.tags = [
                topic
                for topic in self.topics_list
                if topic.lower() in document.body.lower()
            ][:5]
        return document
