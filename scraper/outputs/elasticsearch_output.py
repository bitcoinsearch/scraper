from elasticsearch import Elasticsearch
from typing import Any, List, Optional
import logging
from loguru import logger

from scraper.models import ScrapedDocument, ScraperRunDocument
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

    async def record_run(self, run_document: ScraperRunDocument) -> None:
        """Record statistics for a scraper run"""
        self.es.index(
            index=self.index_name,
            document=run_document.model_dump(exclude_none=True),
        )

    async def _query_runs(
        self,
        source: str,
        must_terms: dict[str, Any] = None,
        size: int = 1,
    ) -> List[ScraperRunDocument]:
        """
        Generic method to query run documents with configurable filters.

        Args:
            source: Name of the source to query
            must_terms: Additional term queries to add to the must clause
            size: Maximum number of documents to return

        Returns:
            List[ScraperRunDocument]: List of matching run documents
        """
        try:
            # Build base query
            must_clauses = [
                {"term": {"source": source.lower()}},
                {"term": {"type": "scraper_run"}},
            ]

            # Add additional term queries if provided
            if must_terms:
                must_clauses.extend({"term": {k: v}} for k, v in must_terms.items())

            query = {
                "query": {"bool": {"must": must_clauses}},
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": size,
            }

            result = self.es.search(index=self.index_name, body=query)
            return [
                ScraperRunDocument(**hit["_source"]) for hit in result["hits"]["hits"]
            ]

        except Exception as e:
            logger.error(f"Error querying runs for {source}: {e}")
            return []

    async def get_last_successful_run(
        self, source: str
    ) -> Optional[ScraperRunDocument]:
        """Get the most recent successful run for a scraper"""
        runs = await self._query_runs(
            source=source, must_terms={"success": True}, size=1
        )
        return runs[0] if runs else None

    async def get_recent_runs(
        self, source: str, limit: int = 10
    ) -> List[ScraperRunDocument]:
        """Get the most recent runs for a source."""
        return await self._query_runs(source=source, size=limit)

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
