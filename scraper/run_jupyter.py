import os
import click
from pathlib import Path
from scraper.config import get_project_root


def get_available_notebooks():
    """Get a list of available notebooks in the notebooks directory."""
    notebooks_dir = Path(get_project_root()) / "notebooks"
    return [f.name for f in notebooks_dir.glob("*.ipynb")]


@click.command()
@click.argument("notebook", required=False, default="playground.ipynb")
@click.option(
    "--list", "list_notebooks", is_flag=True, help="List all available notebooks"
)
def main(notebook, list_notebooks):
    """Run Jupyter notebooks for scraper development.

    If no NOTEBOOK is specified, runs playground.ipynb by default.
    """
    if list_notebooks:
        notebooks = get_available_notebooks()
        click.echo("\nAvailable notebooks:")
        for nb in notebooks:
            click.echo(f"  - {nb}")
        return

    # Set environment variables
    os.environ["CONFIG_PROFILE"] = "development"
    # Additional environment variables can be set here
    # os.environ['ENV_VAR'] = '...'

    # Construct notebook path
    notebook_path = os.path.join(get_project_root(), "notebooks", notebook)

    # Check if notebook exists
    if not os.path.exists(notebook_path):
        available_notebooks = get_available_notebooks()
        click.echo(f"\nError: Notebook '{notebook}' not found.", err=True)
        click.echo("\nAvailable notebooks:")
        for nb in available_notebooks:
            click.echo(f"  - {nb}")
        raise click.Abort()

    # Run Jupyter notebook
    os.execvp("jupyter", ["jupyter", "notebook", notebook_path])


if __name__ == "__main__":
    main()
