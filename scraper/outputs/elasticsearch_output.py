from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk
from datetime import datetime
from typing import List
from loguru import logger

from scraper.models import MetadataDocument, ScrapedDocument
from scraper.config import SourceConfig, settings
from scraper.outputs import AbstractOutput
from scraper.registry import output_registry


@output_registry.register("elasticsearch")
class ElasticsearchOutput(AbstractOutput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.es = None
        self.metadata_prefix = "scrape_metadata_"

    async def _initialize(self):
        try:
            self.es = AsyncElasticsearch(
                cloud_id=settings.CLOUD_ID, api_key=settings.API_KEY, timeout=120
            )
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch: {e}")
            raise

    async def _cleanup(self):
        if self.es:
            await self.es.close()

    async def _index_batch(self, documents: List[ScrapedDocument]):
        try:
            actions = [
                {
                    "_op_type": "index",
                    "_index": self.index_name,
                    "_id": doc.id,
                    "_source": doc.model_dump(exclude_none=True),
                }
                for doc in documents
            ]

            success, failed = await async_bulk(self.es, actions, raise_on_error=False)

            logger.info(f"Successfully indexed {success} documents")
            if failed:
                logger.error(f"Failed to index {len(failed)} documents")
                for item in failed:
                    logger.error(f"Failed document: {item}")
        except Exception as e:
            logger.error(f"Error during bulk indexing: {e}")

    async def get_metadata(self, config: SourceConfig) -> MetadataDocument:
        doc_id = f"{self.metadata_prefix}{config.name}"
        try:
            result = await self.es.get(index=settings.DEFAULT_INDEX, id=f"{doc_id}")
            return MetadataDocument(**result["_source"])
        except NotFoundError:
            logger.info(
                f"No metadata found for {config.domain}. Creating new metadata."
            )
        except Exception as e:
            logger.error(f"Error retrieving metadata for {config.domain}: {e}")
        return MetadataDocument(
            id=doc_id,
            domain=config.domain,
        )

    async def update_metadata(self, metadata: MetadataDocument):
        metadata.updated_at = datetime.now().isoformat()

        try:
            await self.es.index(
                index=settings.DEFAULT_INDEX,
                id=metadata.id,
                body=metadata.model_dump(exclude_none=True),
            )
            logger.info(f"Updated metadata for {metadata.domain}")
        except Exception as e:
            logger.error(f"Error updating metadata for {metadata.domain}: {e}")

    async def cleanup_test_documents(self, index_name: str):
        query = {"query": {"term": {"test_document": True}}}
        try:
            result = await self.es.delete_by_query(index=index_name, body=query)
            logger.info(
                f"Cleaned up {result['deleted']} test documents from index {index_name}"
            )
        except Exception as e:
            logger.error(f"Error cleaning up test documents: {e}")
