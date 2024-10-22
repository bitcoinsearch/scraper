# Notebooks

This directory contains Jupyter notebooks used for development, testing, and analysis purposes within the scraper project.

## Available Notebooks

### 1. `playground.ipynb`

A general-purpose playground notebook for interactively exploring the scraper's functionality. Use this notebook to:
- Test scraper configurations
- Explore scraped data
- Debug scraping issues
- Prototype new features

### 2. `summary_efficiency_analysis.ipynb`

This notebook contains the code and analysis for evaluating the efficiency of our post summarization process. It analyzes the relationship between original post lengths and their summaries across different platforms (Delving Bitcoin, bitcoin-dev mailing list, and lightning-dev mailing list).

The analysis from this notebook was used to:
- Evaluate summarization efficiency across different platforms
- Compare summary lengths with original post lengths
- Analyze differences between original posts and replies
- Generate statistics and visualizations for summary efficiency metrics

The findings from this analysis are published in:
1. [Thread Summaries Workflow Analysis and Proposal](https://github.com/bitcoinsearch/summarizer/issues/61) - Used to support the discussion about improving the summarization workflow
2. [Summary Efficiency Analysis Results](https://github.com/bitcoinsearch/summarizer/issues/62) - Detailed results and conclusions from the analysis

## Running the Notebooks

You can run any notebook in this directory using:

```bash
# Run the default playground notebook
poetry run playground

# Run a specific notebook
poetry run notebook summary_efficiency_analysis.ipynb

# List all available notebooks
poetry run notebook --list
```

This command will:
1. Launch a Jupyter notebook server
2. Set up the necessary environment with access to all scraper modules
3. Use the development configuration profile
4. Open the specified notebook (or playground.ipynb by default)

## Development Guidelines

When creating new notebooks in this directory:
1. Add a clear description at the top of the notebook explaining its purpose
2. Include any necessary setup instructions or prerequisites
3. Document the notebook's purpose and findings in this README
4. If the notebook generates analysis or results used in other documents, include references to those documents

## Environment

All notebooks in this directory have access to:
- All scraper modules and utilities
- Development configuration profile
- Required dependencies as specified in `pyproject.toml`

Make sure you have all required dependencies installed by running:
```bash
poetry install
```

## Note

The notebooks in this directory are primarily for development and analysis purposes. For production scraping tasks, use the CLI commands as documented in the main project README.