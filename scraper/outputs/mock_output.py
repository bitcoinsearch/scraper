import json
from datetime import datetime
import os
from typing import Dict, List, Optional

from loguru import logger

from scraper.models import ScrapedDocument, ScraperRunDocument
from scraper.outputs import AbstractOutput
from scraper.config import settings
from scraper.registry import output_registry


@output_registry.register("mock")
class MockOutput(AbstractOutput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        """Initialize the output file with empty documents and runs arrays"""
        self._write_json(
            {
                "documents": [],
                "runs": [],  # Store runs as an array for future extensibility
            }
        )

    async def _cleanup(self):
        logger.info(
            f"Mock output written to {self.output_file} (excluded fields: {self.excluded_fields})"
        )

    def _write_json(self, data: Dict):
        """Write data to the output file"""
        with open(self.output_file, "w") as f:
            json.dump(data, f, indent=2)

    def _read_json(self) -> Dict:
        """Read data from the output file"""
        if os.path.exists(self.output_file):
            with open(self.output_file, "r") as f:
                return json.load(f)
        return {"documents": [], "runs": []}

    def _append_documents(self, documents: List[Dict]):
        """Append documents to the output file"""
        data = self._read_json()
        data["documents"].extend(documents)
        self._write_json(data)

    async def _index_batch(self, documents: List[ScrapedDocument]):
        """Index a batch of documents"""
        docs_to_index = [
            doc.model_dump(exclude_none=True, exclude=self.excluded_fields)
            for doc in documents
        ]

        self._append_documents(docs_to_index)

    async def get_last_successful_run(
        self, source: str
    ) -> Optional[ScraperRunDocument]:
        """Always return None to simulate no previous runs"""
        return None

    async def record_run(self, run_document: ScraperRunDocument) -> None:
        """Update the runs section of the output file"""
        data = self._read_json()

        # Convert run document to dict and handle datetime serialization
        run_dict = run_document.model_dump(exclude_none=True)

        # Update runs array - keeping just the latest run for now
        data["runs"] = [run_dict]

        self._write_json(data)
