import click
import asyncio
from pathlib import Path
import yaml
from typing import Optional
from loguru import logger
from scraper.config import get_project_root, settings
from scraper.scrapers.scrapy.llm_analyzer import LLMAnalyzer
from scraper.scrapers.scrapy.configuration_validator import ConfigurationValidator
from scraper.scrapers.scrapy.selector_types import (
    ScrapingConfig,
    PageConfig,
    ItemConfig,
    SelectorConfig,
)
from scraper.scrapers.scrapy.spider_config import SpiderConfig


@click.group()
def scrapy():
    """Commands for managing Scrapy-based scrapers."""
    pass


@scrapy.command()
@click.argument("source", required=True)
@click.option("--debug", is_flag=True, help="Enable debug output")
def analyze(source: str, debug: bool):
    """
    Analyze a source and generate its selector configuration using LLM.

    Uses GPT to analyze the HTML structure and suggest selectors for scraping.
    The analysis looks at both index and resource pages to determine optimal
    selectors for content extraction.

    Example usage:
    $ scraper scrapy analyze bitcointalk --debug
    """
    try:
        # Get source configuration
        source_config = settings.get_source_config(source)
        if not source_config:
            raise click.ClickException(f"Source '{source}' not found in sources.yaml")

        # Verify it's a web source
        sources = settings.load_sources()
        if not any(
            src.name.lower() == source.lower() for src in sources.get("web", [])
        ):
            raise click.ClickException(
                f"Source '{source}' is not a web source. "
                "This command is only for web sources using Scrapy."
            )

        if not source_config.analyzer_config:
            raise click.ClickException(
                f"No analyzer configuration found for '{source}'. "
                "Make sure analyzer_config with index_url and resource_url is defined in sources.yaml"
            )

        try:
            # Initialize analyzer
            analyzer = LLMAnalyzer(
                source_config=source_config,
                api_key=settings.OPENAI_API_KEY,
                debug=debug,
            )

            # Run analysis
            logger.info(f"Starting LLM analysis for {source}")
            config = asyncio.run(analyzer.analyze())

            logger.info(f"Successfully generated configuration for {source}")
            if debug:
                logger.info("Configuration preview:")
                logger.info(config)

        except Exception as e:
            raise click.ClickException(f"Analysis failed: {str(e)}")

    except click.ClickException as e:
        click.echo(str(e), err=True)
        raise click.Abort()


def load_spider_config(source_name: str) -> Optional[SpiderConfig]:
    """Load spider configuration for a source."""
    config_path = (
        Path(get_project_root())
        / "scrapy_sources_configs"
        / f"{source_name.lower()}.yaml"
    )

    if not config_path.exists():
        return None

    return SpiderConfig(str(config_path))


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

        if not source_config.analyzer_config:
            raise click.ClickException(
                f"Source '{source}' missing analyzer_config in sources.yaml. "
                "Please add index_url and resource_url configuration."
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


@scrapy.command()
@click.argument("source", required=True)
@click.option(
    "--max-pages",
    default=2,
    help="Maximum number of pages to validate in pagination chain",
)
@click.option(
    "--delay",
    default=1.0,
    help="Delay between requests in seconds",
)
def validate(source: str, max_pages: int, delay: float):
    """
    Validate the Scrapy configuration for a source.

    Tests selectors against live pages to verify they correctly extract content.

    Example usage:
    $ scraper scrapy validate bitcointalk --max-pages 3 --delay 2
    """
    try:
        # Get source configuration
        source_config = settings.get_source_config(source)
        if not source_config:
            raise click.ClickException(f"Source '{source}' not found in sources.yaml")

        # Verify it's a web source
        sources = settings.load_sources()
        if not any(
            src.name.lower() == source.lower() for src in sources.get("web", [])
        ):
            raise click.ClickException(
                f"Source '{source}' is not a web source. "
                "This command is only for web sources using Scrapy."
            )

        if not source_config.analyzer_config:
            raise click.ClickException(
                f"No analyzer configuration found for '{source}'. "
                "Make sure index_url and resource_url are defined in sources.yaml"
            )

        # Load spider configuration
        spider_config = load_spider_config(source)
        if not spider_config:
            raise click.ClickException(
                f"No configuration file found for '{source}' in scrapy_sources_configs/. "
                f"Run 'scraper scrapy init {source}' first."
            )

        if not spider_config.scraping_config:
            raise click.ClickException(
                f"No selectors configuration found in the config file for '{source}'"
            )

        # Initialize validator
        validator = ConfigurationValidator(
            source_name=source,
            source_url=str(source_config.analyzer_config.index_url),
            resource_url=str(source_config.analyzer_config.resource_url),
            scraping_config=spider_config.scraping_config,
            max_pages=max_pages,
            page_delay=delay,
        )

        # Run validation
        click.echo(f"\nValidating Scrapy configuration for {source}...")
        click.echo(
            "This may take a few moments as we test the selectors against live pages.\n"
        )

        # Run validation asynchronously
        result = asyncio.run(validator.validate())

        # Create and display report
        from scraper.scrapers.scrapy.validation_report import create_validation_report

        report = create_validation_report(
            result["source_name"],
            result["index_results"],
            result["resource_results"],
        )

        click.echo(report)

    except click.ClickException as e:
        click.echo(str(e), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        logger.exception("Full traceback:")
        raise click.Abort()
