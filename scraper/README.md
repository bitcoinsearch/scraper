# Scraper

A flexible multi-source scraper application designed to gather information from various types of sources, including GitHub repositories and web pages.

## Features

- Flexible output options (Elasticsearch, mock for testing)
- Extensible architecture for easy addition of new sources and scrapers

## Installation

1. Make sure you have Python 3.11+ installed.
2. Install Poetry if you haven't already: `pip install poetry`
3. Clone this repository and navigate to the project directory.
4. Run `poetry install` to install the dependencies.

## Configuration

- Sources are defined in `sources.yaml`
- Configuration profiles are set in `config.ini` and specified by the `CONFIG_PROFILE` environment variable
  - An example `config.ini.example` file is provided in the repository
  - You can define multiple profiles (e.g., development, production) in this file

## Usage

- Scrape all sources: `poetry run scraper scrape`
- Scrape a specific source: `poetry run scraper scrape --source sourcename`
- List available sources: `poetry run scraper list-sources`
- Show configuration: `poetry run scraper show-config`
- Cleanup test documents: `poetry run scraper cleanup-test-documents`


## Sources Configuration

The scraper uses a registry-based architecture to manage scrapers, processors, and outputs. This design allows for flexible configuration and easy extensibility.
- **Scrapers**: Each scraper is registered with one or more source names. This allows a single scraper implementation to be used for multiple similar sources, or custom scrapers to be created for specific sources.
- **Outputs**: Different output methods (e.g., Elasticsearch, mock) are registered and can be selected at runtime.


### Adding New Sources

1. **Add to `sources.yaml`** under the appropriate type:

   ```yaml
   github:
     - name: NewRepo
       domain: https://github.com/user/new-repo
       url: https://github.com/user/new-repo.git
       # Optional: scraper: CustomScraper
   ```

2. **Register a scraper for the new source**:
   - If the new source can use an existing scraper, add its name to the registration of that scraper:

     ```python
     @scraper_registry.register("BOLTs", "NewRepo")
     class GithubScraper(BaseScraper):
         # ... existing implementation ...
     ```

   - If the new source needs a custom scraper, create a new class and register it with the source's name:

     ```python
     from scraper.registry import scraper_registry
     from scraper.scrapers.github import GithubScraper

     @scraper_registry.register("NewRepo")
     class NewRepoScraper(GithubScraper):
         async def scrape(self):
             # ... custom implementation ...
     ```

3. **Test**: Run the scraper with your new source to ensure it works as expected:
   ```
   scraper scrape --test --output=mock --source NewRepo
   ```

### Adding a New Source Type

If you need to add an entirely new type of source:

1. Add a new top-level key to `sources.yaml` for your new type.
2. Create a default scraper for this new type (e.g., `NewTypeScraper`).

## Development and Testing

### Jupyter Notebook Playground

For development and testing purposes, this project includes a Jupyter notebook playground. This feature allows you to interactively explore the scraper's functionality, test different configurations, and analyze scraped data.

To start the Jupyter notebook playground:

```
poetry run playground
```

This command will launch a Jupyter notebook server and open the [notebooks/playground.ipynb](./notebooks/playground.ipynb) file. The notebook environment will have access to all the scraper's modules and will use the development configuration profile.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
