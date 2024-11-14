from abc import ABC, abstractmethod
from typing import List

from loguru import logger

from scraper.config import SourceConfig, settings
from scraper.models import MetadataDocument, ScrapedDocument


class AbstractOutput(ABC):
    """
    Abstract base class for all output handlers in the system.

    This class defines the common interface that all concrete output
    implementations must adhere to. It provides methods for initializing
    and closing the output, indexing documents, and managing metadata.

    Concrete implementations of this class handle the specifics of
    how data is stored or transmitted (e.g., to a database, file, or API).
    """

    def __init__(self, index_name: str = None, batch_size: int = 100):
        self.batch_size = batch_size
        self.document_buffer: List[ScrapedDocument] = []
        self.index_name = index_name or settings.DEFAULT_INDEX

    async def __aenter__(self):
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.flush_buffer()
        await self._cleanup()

    @abstractmethod
    async def _initialize(self):
        """
        Initialize the output handler.

        This method should perform any necessary setup operations,
        such as establishing database connections or opening file handles.
        """
        pass

    @abstractmethod
    async def _cleanup(self):
        """
        Clean up any resources used by the output.

        This method should perform any necessary cleanup operations,
        such as closing database connections or file handles.
        """
        pass

    @abstractmethod
    async def _index_batch(self, documents: List[ScrapedDocument]):
        """
        Index a batch of documents.

        This method should be implemented by subclasses to define how a batch of documents
        is indexed in the specific output system (e.g., Elasticsearch, file system, etc.).

        Args:
            documents (List[ScrapedDocument]): A list of documents to be indexed.
        """
        pass

    async def index_document(self, document: ScrapedDocument):
        """
        Index a single document.

        This method adds the document to the buffer and flushes the buffer if it reaches the batch size.

        Args:
            document (ScrapedDocument): The document to be indexed.
        """
        self.document_buffer.append(document)
        if len(self.document_buffer) >= self.batch_size:
            await self.flush_buffer()

    async def flush_buffer(self):
        """
        Flush the current buffer of documents.

        This method indexes the current batch of documents in the buffer and clears the buffer.
        It's called automatically when the buffer reaches the batch size, but can also be called manually.
        """
        if self.document_buffer:
            await self._index_batch(self.document_buffer)
            logger.debug(
                f"{self.__class__.__name__}: Indexed {len(self.document_buffer)} documents to {self.index_name}"
            )
            self.document_buffer.clear()

    @abstractmethod
    async def get_metadata(self, config: SourceConfig) -> MetadataDocument:
        """
        Retrieve metadata for a given domain.

        Args:
            source (SourceConfig): The source for which to retrieve metadata.

        Returns:
            MetadataDocument: The metadata associated with the specified source.
        """
        pass

    @abstractmethod
    async def update_metadata(self, metadata: MetadataDocument):
        """
        Update metadata for the source.

        Args:
            metadata (MetadataDocument): The new metadata to associate with the source.
        """
        pass
