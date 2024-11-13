# Scraper

A flexible multi-source scraper application designed to gather information from GitHub repositories and web pages. Leverages both Git-based and Scrapy-based approaches to handle different source types effectively.

## Features

- Flexible output options (Elasticsearch, mock [for testing](#testing-scrapers))
- Extensible architecture for [easy addition of new sources](#adding-new-sources)
- [Configurable processors](#adding-new-processors) for customizing document processing before indexing

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

## Sources Configuration

The scraper uses a registry-based architecture to manage scrapers, processors, and outputs. This design allows for flexible configuration and easy extensibility.

- **Scrapers**: Each scraper is registered with one or more source names. This allows a single scraper implementation to be used for multiple similar sources, or custom scrapers to be created for specific sources.
- **Processors**: Processors are registered by name and can be applied to any source as specified in the configuration.
- **Outputs**: Different output methods (e.g., Elasticsearch, mock) are registered and can be selected at runtime.

### Source Configuration Structure

Sources are configured in `sources.yaml`, which serves as the central source of truth for all scraping configurations.

```yaml
web: # Web-based sources using Scrapy
  - name: BitcoinTalk
    domain: bitcointalk.org
    url: https://bitcointalk.org/index.php?board=6.0
    analyzer_config: # For LLM-based selector generation
      index_url: https://bitcointalk.org/index.php?board=6.0
      resource_url: https://bitcointalk.org/index.php?topic=5499150.0
    processors: # Optional post-processing
      - summarization

github: # Git repository sources
  - name: BitcoinOps
    domain: https://bitcoinops.org
    url: https://github.com/bitcoinops/bitcoinops.github.io.git
    directories: # Optional directory mapping
      _posts/en: post
```

### Adding New Sources

For testing your new source configuration, see the [Development and Testing](#development-and-testing) section.

#### GitHub Source

1. **Add to `sources.yaml`**:

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

#### Web Source

1. **Add source configuration to `sources.yaml`**:

   ```yaml
   web:
     - name: NewSite
       domain: example.com
       url: https://example.com/listing
       analyzer_config: # Required for automatic selector generation
         index_url: https://example.com/listing
         resource_url: https://example.com/example-post
       processors:
         - summarization
   ```

2. **Register with the default scraper**:

   ```python
   from scraper.registry import scraper_registry
   from scraper.scrapers.scrapy import ScrapyScraper

   @scraper_registry.register("NewSite")
   class ScrapyScraper(BaseScraper):
       # ... existing implementation ...
       # Uses the default BaseSpider
   ```

3. **Set up Scrapy configuration**:
   The scraper uses configuration-based scraping, which can be set up in two ways:

   ```bash
   # Option 1: AI-Assisted Configuration
   scraper scrapy analyze newsite    # Generate config using AI analysis

   # Option 2: Manual Configuration
   scraper scrapy init newsite       # Create blank config template
   ```

   Then validate your configuration:
   ```bash
   scraper scrapy validate NewSite
   ```

   For detailed information about Scrapy configuration, see the [Scrapy Configuration Guide](scrapy_sources_configs/README.md).

4. **(Optional) Custom Spider Implementation**:
   If the default scraper doesn't meet your needs (e.g., special date parsing, content processing), you can create a custom spider:

   ```python
   from scraper.registry import scraper_registry
   from scraper.scrapers.scrapy import ScrapyScraper, BaseSpider

   class NewSiteSpider(BaseSpider):
       def parse_date(self, date_str: str) -> Optional[str]:
           # Custom date parsing implementation
           ...

   @scraper_registry.register("NewSite")
   class NewSiteScraper(ScrapyScraper):
       def get_spider_class(self):
           return NewSiteSpider
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

### Testing Scrapers

#### Mock Output

For initial testing without writing to Elasticsearch:

```bash
scraper scrape --output=mock --source sourcename
```

This runs the scraper and outputs the extracted content to a JSON file.

### Test Resources

To test with specific content, add `test_resources` to your source configuration:
To use this feature:

```yaml
github:
  - name: ExampleRepo
    # ... source configuration ...
    test_resources:
      - path/to/test/file.md

web:
  - name: ExampleSite
    # ... source configuration ...
    test_resources:
      - https://example.com/example-post
      - https://example.com/example-post2
```

The scraper will only process the specified test resources instead of scraping the entire source.

This is useful for debugging, testing new processors, or verifying behavior with specific content. Remove or comment out `test_resources` to scrape the entire source.

### Testing with Elasticsearch

When testing Elasticsearch integration:

1. Set `test_mode=True` in `config.ini`:

   ```ini
   [development]
   test_mode = True
   ```

   This flags indexed documents as test documents.

2. Run your tests with the Elasticsearch output:

   ```bash
   scraper scrape --source sourcename
   ```

3. Clean up test documents when done:
   ```bash
   scraper cleanup-test-documents
   ```

This workflow allows you to verify correct document indexing by testing the full pipeline while also ensuring that the test documents are removed after the tests are complete.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
