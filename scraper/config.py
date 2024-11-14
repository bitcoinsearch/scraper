import os
import configparser
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional

from scraper.registry import output_registry, scraper_registry, processor_registry


class SourceConfig(BaseModel):
    name: str
    domain: HttpUrl
    url: HttpUrl
    scraper: Optional[str] = None
    directories: Optional[Dict[str, str]] = None
    index_name: Optional[str] = None
    type: Optional[str] = None
    test_file: Optional[str] = None
    processors: List[str] = []


def get_project_root():
    """
    Find the project root by searching for a specific file.

    This function traverses up the directory tree from the current file's location
    until it finds a directory containing 'pyproject.toml', which is assumed to be
    the project root.

    Assumptions:
    1. The project uses Poetry and thus has a pyproject.toml file in its root.
    2. The function has permission to read the directory structure.
    3. The project root is not beyond the file system root (/).

    Returns:
        str: The absolute path to the project root directory.

    Raises:
        Exception: If the project root cannot be found.
    """
    current_path = os.path.abspath(__file__)
    while current_path != "/":
        if os.path.exists(os.path.join(current_path, "cli.py")):
            return current_path
        current_path = os.path.dirname(current_path)
    raise Exception("Project root not found")


def read_config(profile: str):
    config = configparser.ConfigParser()
    config_path = os.path.join(get_project_root(), "config.ini")
    config.read(config_path)
    try:
        return config[profile]
    except KeyError:
        raise KeyError(f"Configuration profile '{profile}' not found in {config_path}")


class Settings:
    def __init__(self):
        # Reload environment variables from .env file
        load_dotenv(override=True)

        # Load configuration from config.ini
        self.PROFILE = os.getenv("CONFIG_PROFILE", "DEFAULT")
        self.config = read_config(self.PROFILE)

        # Other settings
        self.DATA_DIR = os.getenv("DATA_DIR", "./data")
        self.DEFAULT_INDEX = os.getenv("INDEX", "default_index")

    def load_sources(self) -> Dict[str, List[SourceConfig]]:
        sources_path = os.path.join(get_project_root(), "sources.yaml")
        try:
            with open(sources_path, "r") as file:
                data = yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Warning: {sources_path} not found. Using empty sources.")
            return {}

        sources = {}
        for source_type, source_list in data.items():
            sources[source_type] = [SourceConfig(**source) for source in source_list]

        return sources

    @property
    def registered_output_types(self):
        return output_registry.get_all()

    @property
    def registered_scraper_types(self):
        return scraper_registry.get_all()

    @property
    def registered_processor_types(self):
        return processor_registry.get_all()

    def get_config_overview(self):
        overview = "Configuration Settings:\n"
        overview += f"PROFILE: {self.PROFILE}\n"
        overview += f"DATA_DIR: {self.DATA_DIR}\n"
        overview += f"DEFAULT_INDEX: {self.DEFAULT_INDEX}\n"
        overview += f"CLOUD_ID: {'Set' if self.CLOUD_ID else 'Not Set'}\n"
        overview += f"API_KEY: {'Set' if self.API_KEY else 'Not Set'}\n"

        # Add config.ini settings
        overview += "\nSettings from config.ini:\n"
        for key, value in self.config.items():
            overview += f"{key}: {value}\n"

        return overview

    @staticmethod
    def _get_env_variable(var_name, custom_message=None):
        value = os.getenv(var_name)
        if not value:
            error_message = (
                custom_message
                or f"{var_name} is not set in the environment or .env file. Please set it and restart the application."
            )
            raise Exception(error_message)
        return value

    @property
    def CLOUD_ID(self):
        return self._get_env_variable(
            "CLOUD_ID",
            "CLOUD_ID is not set in the environment or .env file. Please set it to use Elasticsearch.",
        )

    @property
    def API_KEY(self):
        return self._get_env_variable(
            "API_KEY",
            "API_KEY is not set in the environment or .env file. Please set it to use Elasticsearch.",
        )

    @property
    def OPENAI_API_KEY(self):
        return self._get_env_variable(
            "OPENAI_API_KEY",
            "OPENAI_API_KEY is not set in the environment or .env file. Please set it to use OpenAI.",
        )


# Initialize the Settings class and expose an instance
settings = Settings()

__all__ = ["settings"]
