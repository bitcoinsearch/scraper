import json
from pathlib import Path
from typing import List
from loguru import logger

from scraper.config import get_project_root
from scraper.models import ScrapedDocument
from .base_processor import BaseProcessor
from scraper.registry import processor_registry


@processor_registry.register("topic_extractor")
class TopicExtractorProcessor(BaseProcessor):
    def __init__(self):
        self.topics_list = self.load_topics()

    def load_topics(self) -> List[str]:
        topics_path = Path(get_project_root()) / "processors" / "topics_list.json"
        try:
            with open(topics_path, "r") as f:
                return json.load(f)["topics"]
        except FileNotFoundError:
            logger.warning(
                f"Topics file not found at {topics_path}. Using empty topics list."
            )
            return []
        except json.JSONDecodeError:
            logger.error(
                f"Invalid JSON in topics file: {topics_path}. Using empty topics list."
            )
            return []
        except KeyError:
            logger.error(
                f"Missing 'topics' key in topics file: {topics_path}. Using empty topics list."
            )
            return []

    async def process(self, document: ScrapedDocument) -> ScrapedDocument:
        # Placeholder logic - replace with actual topic extraction
        if document.body:
            document.tags = [
                topic
                for topic in self.topics_list
                if topic.lower() in document.body.lower()
            ][:5]
        return document
