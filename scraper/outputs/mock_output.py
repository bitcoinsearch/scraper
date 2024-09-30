import json
from datetime import datetime
from typing import Dict, List

from loguru import logger

from scraper.models import MetadataDocument, ScrapedDocument, SourceConfig
from scraper.outputs import AbstractOutput
from scraper.config import settings
from scraper.registry import output_registry


@output_registry.register("mock")
class MockOutput(AbstractOutput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata: Dict[str, Dict] = {}
        self.output_file = (
            f"mock_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        self.excluded_fields = [
            field.strip()
            for field in settings.config.get("mock_output_excluded_fields", "").split(
                ","
            )
        ]

    async def _initialize(self):
        self._write_json({"documents": [], "metadata": {}})

    async def _cleanup(self):
        logger.info(
            f"Mock output written to {self.output_file} (excluded fields: {self.excluded_fields})"
        )

    def _write_json(self, data: Dict):
        with open(self.output_file, "w") as f:
            json.dump(data, f, indent=2)

    def _append_json(self, data: List[Dict]):
        with open(self.output_file, "r+") as f:
            file_data = json.load(f)
            file_data["documents"].extend(data)
            f.seek(0)
            json.dump(file_data, f, indent=2)
            f.truncate()

    async def _index_batch(self, documents: List[ScrapedDocument]):
        docs_to_index = [
            doc.model_dump(exclude_none=True, exclude=self.excluded_fields)
            for doc in documents
        ]

        self._append_json(docs_to_index)

    async def get_metadata(self, config: SourceConfig) -> MetadataDocument:
        doc_id = config.name.lower()
        metadata = self.metadata.get(
            doc_id,
            {
                "id": doc_id,
                "domain": str(config.domain),
            },
        )
        return MetadataDocument(**metadata)

    async def update_metadata(self, metadata: MetadataDocument):
        self.metadata[metadata.domain] = metadata.model_dump()
        with open(self.output_file, "r+") as f:
            file_data = json.load(f)
            file_data["metadata"] = self.metadata
            f.seek(0)
            json.dump(file_data, f, indent=2)
            f.truncate()
        logger.info(f"Updated metadata for {metadata.domain}")
