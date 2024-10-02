from scraper.models import ScrapedDocument
from .base_processor import BaseProcessor
from scraper.registry import processor_registry


@processor_registry.register("vector_embeddings")
class VectorEmbeddingsProcessor(BaseProcessor):
    async def process(self, document: ScrapedDocument) -> ScrapedDocument:
        # Placeholder logic - replace with actual vector embedding generation
        if document.summary:
            # This is just a dummy representation, not a real embedding
            document.summary_vector_embeddings = [
                float(ord(c)) for c in document.summary[:10]
            ]
        return document
