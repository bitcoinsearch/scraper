# Scraper

A flexible multi-source scraper application designed to gather information from various types of sources, including GitHub repositories and web pages.

## Features

- Flexible output options (Elasticsearch, mock for testing)
- Extensible architecture for easy addition of new sources and scrapers
- Configurable processors for customizing document processing before indexing

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
- **Processors**: Processors are registered by name and can be applied to any source as specified in the configuration.
- **Outputs**: Different output methods (e.g., Elasticsearch, mock) are registered and can be selected at runtime.


### Adding New Sources

1. **Add to `sources.yaml`** under the appropriate type:

   ```yaml
   github:
     - name: NewRepo
       domain: https://github.com/user/new-repo
       url: https://github.com/user/new-repo.git
       processors:
         - processor1
         - processor2
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

## Adding New Processors

Processors are used to perform additional operations on scraped documents before they are indexed. To add a new processor:

1. Create a new Python file in the `scraper/processors` directory. Name it after your processor, e.g., `my_new_processor.py`.

2. In this file, create a class that inherits from `BaseProcessor` and register it with the `processor_registry`:

   ```python
   from scraper.models import ScrapedDocument
   from scraper.processors.base_processor import BaseProcessor
   from scraper.registry import processor_registry

   @processor_registry.register("my_new_processor")
   class MyNewProcessor(BaseProcessor):
       async def process(self, document: ScrapedDocument) -> ScrapedDocument:
           # Implement your processing logic here
           # Modify the document as needed
           return document
   ```

3. Implement the `process` method. This method should take a `ScrapedDocument` as input, perform some operations on it, and return the modified `ScrapedDocument`.

4. If your processor requires any initialization or configuration, you can add an `__init__` method to the class.

5. Update the `ScrapedDocument` model in `scraper/models.py` if your processor adds any new fields to the document.

6. To use the new processor, add its name to the `processors` list in the `sources.yaml` file for the sources where you want to apply it:

   ```yaml
   github:
     - name: ExampleRepo
       domain: https://github.com/example/repo
       url: https://github.com/example/repo.git
       processors:
         - existing_processor
         - my_new_processor
   ```

7. The processor will be automatically loaded and instantiated by the `ScraperFactory` when it's listed in the `sources.yaml` file.

## Development and Testing

### Jupyter Notebook Playground

For development and testing purposes, this project includes a Jupyter notebook playground. This feature allows you to interactively explore the scraper's functionality, test different configurations, and analyze scraped data.

To start the Jupyter notebook playground:

```
poetry run playground
```

This command will launch a Jupyter notebook server and open the [notebooks/playground.ipynb](./notebooks/playground.ipynb) file. The notebook environment will have access to all the scraper's modules and will use the development configuration profile.

### Testing with Specific Files

During testing, you can specify a single file to be scraped for a particular source. This is helpful when you want to test the scraper's behavior with a known file or debug issues with specific content.

To use this feature:

1. In the `sources.yaml` file, add a `test_file` field to the source configuration:

   ```yaml
   github:
     - name: ExampleRepo
       domain: https://github.com/example/repo
       url: https://github.com/example/repo.git
       processors:
         - processor1
         - processor2
       test_file: path/to/test/file.md
   ```

2. When you run the scraper with this configuration, it will only process the specified `test_file` instead of scraping the entire source.

This is useful for debugging, testing new processors, or verifying behavior with specific content. Remove or comment out `test_file` to scrape the entire source.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
