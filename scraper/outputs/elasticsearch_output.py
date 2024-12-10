from elasticsearch import Elasticsearch, NotFoundError
from datetime import datetime
from typing import List
import logging
from loguru import logger

from scraper.models import MetadataDocument, ScrapedDocument, SourceConfig
from scraper.config import settings
from scraper.outputs import AbstractOutput
from scraper.registry import output_registry


@output_registry.register("elasticsearch")
class ElasticsearchOutput(AbstractOutput):
    """
    Handles document indexing and retrieval using synchronous Elasticsearch client.
    Leverages AbstractOutput's batching mechanism for efficient indexing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.es = None
        self.metadata_prefix = "scrape_metadata_"

        # Configure logging levels for noisy libraries
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
        logging.getLogger("elastic_transport.transport").setLevel(logging.WARNING)

    async def _initialize(self):
        """Set up the Elasticsearch client."""
        try:
            self.es = Elasticsearch(
                cloud_id=settings.CLOUD_ID, api_key=settings.API_KEY, timeout=120
            )
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch: {e}")
            raise

    async def _cleanup(self):
        """Clean up Elasticsearch client resources."""
        if self.es:
            self.es.close()

    async def _index_batch(self, documents: List[ScrapedDocument]):
        """
        Index a batch of documents directly using Elasticsearch.
        Uses AbstractOutput's batching mechanism.
        """
        try:
            # Process documents one by one in the batch
            for doc in documents:
                try:
                    self.es.index(
                        index=self.index_name,
                        id=doc.id,
                        document=doc.model_dump(exclude_none=True),
                    )
                except Exception as e:
                    logger.error(f"Failed to index document {doc.id}: {e}")
                    continue

            logger.info(f"Successfully indexed batch of {len(documents)} documents")

        except Exception as e:
            logger.error(f"Error during batch indexing: {e}")
            logger.exception("Full traceback:")

    async def get_metadata(self, config: SourceConfig) -> MetadataDocument:
        """
        Retrieve metadata document for a source.
        Creates new metadata if none exists for the source.
        """
        doc_id = f"{self.metadata_prefix}{config.name}"
        try:
            result = self.es.get(index=settings.DEFAULT_INDEX, id=doc_id)
            return MetadataDocument(**result["_source"])
        except NotFoundError:
            logger.info(
                f"No metadata found for {config.domain}. Creating new metadata."
            )
        except Exception as e:
            logger.error(f"Error retrieving metadata for {config.domain}: {e}")

        return MetadataDocument(
            id=doc_id,
            domain=str(config.domain),
        )

    async def update_metadata(self, metadata: MetadataDocument):
        """Update metadata document in Elasticsearch."""
        metadata.updated_at = datetime.now().isoformat()

        try:
            self.es.index(
                index=settings.DEFAULT_INDEX,
                id=metadata.id,
                document=metadata.model_dump(exclude_none=True),
            )
            logger.info(f"Updated metadata for {metadata.domain}")
        except Exception as e:
            logger.error(f"Error updating metadata for {metadata.domain}: {e}")

    async def cleanup_test_documents(self, index_name: str):
        """Remove all test documents from the specified index."""
        query = {"query": {"term": {"test_document": True}}}
        try:
            result = self.es.delete_by_query(index=index_name, body=query)
            logger.info(
                f"Cleaned up {result['deleted']} test documents from index {index_name}"
            )
        except Exception as e:
            logger.error(f"Error cleaning up test documents: {e}")
            logger.exception("Full traceback:")
            raise

    async def create_index_with_mapping(self, index_name: str, mapping: dict):
        """
        Create an index with a specific mapping.
        If the index exists, raise an error.
        """
        try:
            if self.es.indices.exists(index=index_name):
                raise ValueError(f"Index {index_name} already exists")

            self.es.indices.create(index=index_name, body=mapping)
            logger.info(f"Created index {index_name} with custom mapping")

        except Exception as e:
            logger.error(f"Error creating index {index_name}: {e}")
            raise
