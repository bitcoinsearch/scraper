import os
import sys
import subprocess

from scraper.config import get_project_root


def main():
    # Set environment variables
    os.environ["CONFIG_PROFILE"] = "development"

    # Additional environment variables can be set here
    # os.environ['CLOUD_ID'] = '...'
    # os.environ['API_KEY'] = '...'

    # Run Jupyter notebook
    notebook_path = os.path.join(get_project_root(), "playground.ipynb")
    os.execvp("jupyter", ["jupyter", "notebook", notebook_path])


if __name__ == "__main__":
    main()
