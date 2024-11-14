import click
import asyncio

from loguru import logger

from scraper.config import settings
from scraper.outputs import ElasticsearchOutput
from scraper.scraper_factory import ScraperFactory


@click.group()
def cli():
    pass


async def async_scrape(source_name, output_type):
    """
    This function coordinates the scraping process for all sources or a specific source.

    The process works as follows:
    1. Load all source configurations from the settings.
    2. Initialize the appropriate output handler.
    3. Iterate through all source types and their respective sources.
    4. For each source, use the ScraperFactory to create the appropriate scraper.
    5. Run the scraper for each source and handle any errors that occur.

    This design allows for easy addition of new source types and scrapers, as the
    function doesn't need to know the specifics of each scraper implementation.

    Args:
        source_name (str): Name of a specific source to scrape, or None to scrape all sources
        output_type (str): The type of output to use ('mock' or 'elasticsearch')
    """
    sources = settings.load_sources()
    all_sources = [src for source_list in sources.values() for src in source_list]

    if source_name:
        sources_to_scrape = [
            src for src in all_sources if src.name.lower() == source_name.lower()
        ]
        if not sources_to_scrape:
            click.echo(
                f"Error: Source '{source_name}' not found. Please check the source name and try again."
            )
            return

        for src in sources_to_scrape:
            try:
                scraper = ScraperFactory.create_scraper(src, output_type)
                await scraper.run()
            except Exception as e:
                click.echo(f"Error scraping {src.name}: {str(e)}")
                logger.exception("Full traceback:")


@cli.command()
@click.option("--source", help="Name of the source to scrape")
@click.option(
    "--output",
    type=click.Choice(settings.registered_output_types),
    default="elasticsearch",
    help="Type of output to use",
)
def scrape(source, output):
    asyncio.run(async_scrape(source, output))


async def async_cleanup_test_documents(index):
    output = ElasticsearchOutput()
    try:
        await output.initialize()
        await output.cleanup_test_documents(index)
        click.echo(f"Cleaned up test documents from index {index}")
    except Exception as e:
        click.echo(f"Failed to clean up test documents: {e}")
    finally:
        await output.close()


@cli.command()
@click.option(
    "--index", default=settings.DEFAULT_INDEX, help="Name of the index to clean."
)
def cleanup_test_documents(index):
    asyncio.run(async_cleanup_test_documents(index))


@cli.command()
def list_sources():
    sources = settings.load_sources()
    total_sources = 0

    for source_type, source_list in sources.items():
        click.echo(f"\n{source_type.upper()}:")
        for source in source_list:
            click.echo(f"  {source.name:<20} {source.domain}")
        total_sources += len(source_list)

    click.echo(f"\nTotal number of sources: {total_sources}")


@cli.command()
def show_config():
    click.echo(settings.get_config_overview())


if __name__ == "__main__":
    cli()
