import click
from twisted.internet import asyncioreactor, defer
from twisted.internet.task import react
from loguru import logger

from scraper.commands.elastic import elastic
from scraper.commands.scrapy import scrapy
from scraper.commands.github import github
from scraper.config import settings
from scraper.scraper_factory import ScraperFactory


# Technical implementation note:
# We use Twisted's reactor to manage async operations because we're integrating two different
# async frameworks: Scrapy (Twisted-based) and the Elasticsearch client (asyncio-based).
# The reactor pattern ensures proper coordination between these frameworks and prevents
# event loop conflicts. This affects all async operations in the CLI (scraping, cleanup, etc).


@click.group()
def cli():
    """Scrape data from a variety of sources."""
    pass


cli.add_command(scrapy)
cli.add_command(github)
cli.add_command(elastic)


def run_in_reactor(coro):
    """Bridge between coroutines and Twisted's deferred system."""
    return defer.ensureDeferred(coro)


@cli.command()
@click.option("--source", help="Name of the source to scrape from sources.yaml")
@click.option(
    "--output",
    type=click.Choice(settings.registered_output_types),
    default="elasticsearch",
    help="Where to send the scraped data",
)
def scrape(source, output):
    """
    Start scraping operations for one or all sources.

    If --source is provided, scrapes only that source. Otherwise, scrapes all
    sources defined in sources.yaml. The scraped data is sent to the specified
    output (elasticsearch by default).

    Example usage:
    $ scraper scrape --source bitcointalk
    $ scraper scrape  # scrapes all sources
    """
    try:
        asyncioreactor.install()
    except Exception:
        pass

    def run_scraper(reactor):
        async def run_scraping():
            sources = settings.load_sources()
            all_sources = [
                src for source_list in sources.values() for src in source_list
            ]

            if source:
                sources_to_scrape = [
                    src for src in all_sources if src.name.lower() == source.lower()
                ]
                if not sources_to_scrape:
                    click.echo(
                        f"Error: Source '{source}' not found. Please check the source name and try again."
                    )
                    return

                for src in sources_to_scrape:
                    try:
                        scraper = ScraperFactory.create_scraper(src, output)
                        await scraper.run()
                    except Exception as e:
                        click.echo(f"Error scraping {src.name}: {str(e)}")
                        logger.exception("Full traceback:")

        return run_in_reactor(run_scraping())

    react(run_scraper)


@cli.command()
def list_sources():
    """
    List all configured sources and their domains.

    This command shows all sources defined in sources.yaml, organized by type
    (e.g., GitHub repositories, web sources).

    Example usage:
    $ scraper list-sources
    """
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
    """
    Display the current configuration settings.

    Shows the active configuration profile, paths, and other settings
    that affect the scraper's behavior.

    Example usage:
    $ scraper show-config
    """
    click.echo(settings.get_config_overview())


if __name__ == "__main__":
    cli()
