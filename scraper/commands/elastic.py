import click
import json
from pathlib import Path
from twisted.internet.task import react
from twisted.internet import defer

from scraper.outputs import ElasticsearchOutput


def run_in_reactor(coro):
    """Bridge between coroutines and Twisted's deferred system."""
    return defer.ensureDeferred(coro)


@click.group()
def elastic():
    """Commands for managing Elasticsearch indices."""
    pass


@elastic.command()
@click.argument("index_name")
@click.argument("mapping_file", type=click.Path(exists=True, path_type=Path))
@click.option("--force", is_flag=True, help="Delete index if it exists")
def init_index(index_name: str, mapping_file: Path, force: bool):
    """
    Initialize an Elasticsearch index with a custom mapping.

    Example usage:
    $ scraper elastic init-index my_index mappings/github_metadata.json
    $ scraper elastic init-index my_index mappings/github_metadata.json --force
    """
    try:
        from twisted.internet import asyncioreactor

        asyncioreactor.install()
    except Exception:
        pass

    def run_init(reactor):
        async def initialize():
            output = ElasticsearchOutput(index_name=index_name)

            try:
                with open(mapping_file) as f:
                    mapping = json.load(f)
            except json.JSONDecodeError:
                raise click.ClickException(
                    f"Invalid JSON in mapping file: {mapping_file}"
                )
            except Exception as e:
                raise click.ClickException(f"Error reading mapping file: {e}")

            async with output:
                if force and output.es.indices.exists(index=index_name):
                    output.es.indices.delete(index=index_name)
                    click.echo(f"Deleted existing index: {index_name}")

                await output.create_index_with_mapping(index_name, mapping)
                click.echo(
                    f"Successfully created index {index_name} with mapping from {mapping_file}"
                )

        return run_in_reactor(initialize())

    react(run_init)


@elastic.command()
@click.argument("index_name")
@click.option(
    "--test-docs-only",
    is_flag=True,
    help="Remove only documents marked as test_document=True",
)
def cleanup_index(index_name: str, test_docs_only: bool):
    """
    Remove documents from the specified Elasticsearch index.

    By default removes all documents. Use --test-docs-only to remove only test documents.

    Example usage:
    $ scraper elastic cleanup-index my_index
    $ scraper elastic cleanup-index my_index --test-docs-only
    """
    try:
        from twisted.internet import asyncioreactor

        asyncioreactor.install()
    except Exception:
        pass

    def run_cleanup(reactor):
        output = ElasticsearchOutput(index_name=index_name)

        async def cleanup():
            async with output:
                if not output.es.indices.exists(index=index_name):
                    click.echo(f"Index {index_name} does not exist")
                    return

                if test_docs_only:
                    await output.cleanup_test_documents(index_name)
                    click.echo(f"Cleaned up test documents from index {index_name}")
                else:
                    output.es.delete_by_query(
                        index=index_name, body={"query": {"match_all": {}}}
                    )
                    click.echo(f"Removed all documents from index {index_name}")

        return run_in_reactor(cleanup())

    react(run_cleanup)


@elastic.command()
@click.argument("index_name")
def show_mapping(index_name: str):
    """
    Show the current mapping for an index.

    Example usage:
    $ scraper elastic show-mapping my_index
    """
    try:
        from twisted.internet import asyncioreactor

        asyncioreactor.install()
    except Exception:
        pass

    def run_show(reactor):
        async def show():
            output = ElasticsearchOutput(index_name=index_name)

            async with output:
                if not output.es.indices.exists(index=index_name):
                    click.echo(f"Index {index_name} does not exist")
                    return

                mapping = output.es.indices.get_mapping(index=index_name)
                click.echo(json.dumps(mapping.body, indent=2))

        return run_in_reactor(show())

    react(run_show)
