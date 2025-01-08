from datetime import datetime
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

                # Define query based on the cleanup type
                if test_docs_only:
                    query = {"query": {"term": {"test_document": True}}}
                    operation_desc = "test documents"
                else:
                    query = {"query": {"match_all": {}}}
                    operation_desc = "documents"

                try:
                    # First count how many documents will be affected
                    count_result = output.es.count(index=index_name, body=query)
                    doc_count = count_result["count"]

                    # Ask for confirmation
                    if not click.confirm(
                        f"\nWarning: {doc_count} {operation_desc} will be deleted from index '{index_name}'. Do you want to continue?"
                    ):
                        click.echo("Operation cancelled")
                        return

                    # Proceed with deletion
                    delete_result = output.es.delete_by_query(
                        index=index_name, body=query
                    )

                    # Print detailed deletion results
                    click.echo("\nDeletion Results:")
                    click.echo(
                        f"Total {operation_desc} deleted: {delete_result['deleted']}"
                    )
                    click.echo(f"Total batches: {delete_result['batches']}")
                    click.echo(f"Documents that failed: {delete_result['failures']}")
                    click.echo(f"Time taken: {delete_result['took']}ms")

                    if delete_result.get("failures"):
                        click.echo("\nFailures encountered:")
                        for failure in delete_result["failures"]:
                            click.echo(f"Document ID: {failure['_id']}")
                            click.echo(f"Error: {failure.get('error')}")
                            click.echo("---")

                except Exception as e:
                    click.echo(f"Error during cleanup: {e}", err=True)
                    raise click.ClickException(str(e))

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


@elastic.command()
@click.argument("index_name")
@click.argument("source")
@click.option("--limit", default=10, help="Number of most recent runs to show")
def show_runs(index_name: str, source: str, limit: int):
    """
    Show recent scraper runs for a source.

    Example usage:
        $ scraper elastic show-runs my_index bitcointalk
        $ scraper elastic show-runs my_index bitcointalk --limit 5
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
                runs = await output.get_recent_runs(source, limit)

                if not runs:
                    click.echo(f"No runs found for source: {source}")
                    return

                click.echo(f"\nMost recent {len(runs)} runs for {source}:")
                for run in runs:
                    click.echo("\n" + "-" * 40)
                    # Format timestamps for better readability
                    started = datetime.fromisoformat(run.started_at).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    finished = datetime.fromisoformat(run.finished_at).strftime(
                        "%H:%M:%S"
                    )  # Only time for finish
                    duration = datetime.fromisoformat(
                        run.finished_at
                    ) - datetime.fromisoformat(run.started_at)
                    duration_str = str(duration).split(".")[0]  # Remove microseconds
                    click.echo(
                        f"Time: {started} -> {finished} (duration: {duration_str})"
                    )
                    click.echo(f"Success: {run.success}")
                    if run.error_message:
                        click.echo(f"Error: {run.error_message}")
                    if run.stats:
                        click.echo(
                            f"Resources to process: {run.stats.resources_to_process}"
                        )
                        click.echo(f"Documents indexed: {run.stats.documents_indexed}")
                    if run.last_commit_hash:
                        click.echo(f"Last commit: {run.last_commit_hash[:8]}")

        return run_in_reactor(show())

    react(run_show)
