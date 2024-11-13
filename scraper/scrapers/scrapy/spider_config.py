from pathlib import Path
import yaml
from loguru import logger
from typing import Dict

from scraper.scrapers.scrapy.selector_types import ScrapingConfig


class SpiderConfig:
    """Handles loading and validation of spider selectors configuration"""

    def __init__(self, config_path: str, create_if_missing: bool = False):
        """
        Initialize spider configuration.

        Args:
            config_path: Path to the configuration file
            create_if_missing: If True, create an empty configuration if file doesn't exist
        """
        self.config_path = Path(config_path)

        if not self.config_path.exists():
            if create_if_missing:
                self._create_empty_config()
            else:
                raise FileNotFoundError(f"Config file not found: {config_path}")

        self._load_config()

    def _create_empty_config(self):
        """Create a new configuration file with empty selectors structure"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        empty_config = {"selectors": {"index_page": {}, "resource_page": {}}}
        self._save_config(empty_config)
        logger.info(f"Created new configuration file at {self.config_path}")

    def _load_config(self):
        """Load configuration from file"""
        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f) or {}

        # Validate basic structure
        if "selectors" not in self.config:
            self.config["selectors"] = {}
            self._save_config(self.config)

        # Validate selectors configuration using pydantic if not empty
        if self.config["selectors"]:
            self.scraping_config = ScrapingConfig(**self.config["selectors"])
        else:
            self.scraping_config = None

    def update_config(self, selector_config: Dict):
        """Update the config file with new scraping configuration"""
        # Validate config data using pydantic
        config = ScrapingConfig(**selector_config)

        self.config["selectors"] = config.model_dump(exclude_none=True)
        self.scraping_config = config
        self._save_config(self.config)
        logger.info(f"Updated configuration at {self.config_path}")

    def _save_config(self, config_data: Dict):
        """Save configuration to file"""
        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f, sort_keys=False)
