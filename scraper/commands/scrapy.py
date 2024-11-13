import click
from pathlib import Path
import yaml
from loguru import logger
from scraper.config import get_project_root, settings
from scraper.scrapers.scrapy.selector_types import (
    ScrapingConfig,
    PageConfig,
    ItemConfig,
    SelectorConfig,
)


@click.group()
def scrapy():
    """Commands for managing Scrapy-based scrapers."""
    pass


def create_empty_config() -> ScrapingConfig:
    """Create an empty scraping configuration using selector type models."""
    return ScrapingConfig(
        index_page=PageConfig(
            items=ItemConfig(
                item_selector=SelectorConfig(
                    selector="",
                    attribute="href",
                ),
            ),
            next_page=SelectorConfig(
                selector="",
                attribute="href",
            ),
        ),
        resource_page=PageConfig(
            items=ItemConfig(
                item_selector=SelectorConfig(
                    selector="",
                    multiple=True,
                ),
                title=SelectorConfig(selector=""),
                author=SelectorConfig(selector=""),
                date=SelectorConfig(selector=""),
                content=SelectorConfig(selector=""),
                url=SelectorConfig(
                    selector="",
                    attribute="href",
                ),
            ),
            next_page=SelectorConfig(
                selector="",
                attribute="href",
            ),
        ),
    )


@scrapy.command()
@click.argument("source", required=True)
def init(source: str):
    """
    Initialize a Scrapy configuration for a source defined in sources.yaml.

    Creates an empty selector configuration file for a web source that's
    already defined in sources.yaml.

    Example usage:
    $ scraper scrapy init example-site
    """
    try:
        # Get source configuration
        source_config = settings.get_source_config(source)
        if not source_config:
            raise click.ClickException(
                f"Source '{source}' not found in sources.yaml. "
                "Please add the source configuration first."
            )

        # Verify it's a web source
        sources = settings.load_sources()
        if not any(
            src.name.lower() == source.lower() for src in sources.get("web", [])
        ):
            raise click.ClickException(
                f"Source '{source}' is not a web source. "
                "This command is only for web sources using Scrapy."
            )

        # Create empty selector configuration
        config_dir = Path(get_project_root()) / "scrapy_sources_configs"
        config_dir.mkdir(exist_ok=True)

        config_file = config_dir / f"{source.lower()}.yaml"
        if config_file.exists():
            raise click.ClickException(
                f"Configuration file already exists at {config_file}"
            )

        # Create configuration using Pydantic models
        config = create_empty_config()

        # Convert to dictionary and save
        config_dict = {"selectors": config.model_dump(exclude_none=True)}
        with open(config_file, "w") as f:
            yaml.dump(config_dict, f, sort_keys=False, default_flow_style=False)

        click.echo(f"Created selector configuration template at {config_file}")
        click.echo("\nNext steps:")
        click.echo("1. Add selectors to the configuration file")
        click.echo(
            f"2. Run 'scraper scrapy validate {source}' to test your configuration"
        )

    except Exception as e:
        click.echo(f"Error initializing Scrapy configuration: {str(e)}", err=True)
        logger.exception("Full traceback:")
        raise click.Abort()
