import click
import json
from pathlib import Path
from loguru import logger

from scraper.config import settings, get_project_root
from scraper.registry import scraper_registry


@click.group()
def github():
    """Commands for managing GitHub-based scrapers."""
    pass


@github.command()
@click.argument("source")
@click.option(
    "--all-values",
    is_flag=True,
    help="Store all unique values for each field instead of just examples",
)
@click.option(
    "--output-file",
    type=click.Path(),
    help="Output file path. Defaults to analysis_{source}.json in the project root",
)
def analyze(source: str, all_values: bool, output_file: str):
    """
    Analyze metadata fields present in markdown files of a GitHub repository.

    Scans all markdown files in the repository and analyzes their metadata/front matter
    to discover what fields are used, their frequency, types, and example values.

    Example usage:
    $ scraper github analyze bips
    $ scraper github analyze bips --all-values
    $ scraper github analyze bips --output-file custom_path.json
    """
    try:
        # Get source configuration
        source_config = settings.get_source_config(source)
        if not source_config:
            raise click.ClickException(f"Source '{source}' not found in sources.yaml")

        # Verify it's a GitHub source
        sources = settings.load_sources()
        if not any(
            src.name.lower() == source.lower() for src in sources.get("github", [])
        ):
            raise click.ClickException(
                f"Source '{source}' is not a GitHub source. "
                "This command is only for GitHub repositories."
            )

        # Create scraper instance
        scraper_class = scraper_registry.get(source_config.name)
        scraper = scraper_class(source_config, output=None, processor_manager=None)

        # Run analysis if the scraper supports it
        if not hasattr(scraper, "analyze_metadata"):
            raise click.ClickException(
                f"Scraper for '{source}' does not support metadata analysis."
            )

        # Run analysis
        logger.info(f"Analyzing metadata fields in {source}...")
        analysis = scraper.analyze_metadata(store_all_values=all_values)

        # Determine output file path
        if not output_file:
            output_file = Path(get_project_root()) / f"analysis_{source.lower()}.json"

        # Save analysis to file
        with open(output_file, "w") as f:
            json.dump(analysis, f, indent=2)

        logger.info(f"Analysis saved to {output_file}")

    except click.ClickException as e:
        click.echo(str(e), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        logger.exception("Full traceback:")
        raise click.Abort()
