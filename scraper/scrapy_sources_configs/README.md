# Scrapy Spider Configurations

This directory contains YAML configuration files that define how Scrapy-based spiders should scrape specific websites. Each configuration follows a three-level scraping pattern:

1. **Index Pages**: Pages that list multiple resources (e.g., forum board, blog listing)
2. **Resource Pages**: Individual pages that contain content (e.g., forum thread, blog post)
3. **Items**: The actual content units within resource pages

## Configuration Management

### Prerequisites

Before setting up a Scrapy configuration, the source must be defined in `sources.yaml` under the `web` section with the following information:

```yaml
web:
  - name: ExampleSite
    domain: example.com
    url: https://example.com/blog
```

### CLI Commands

The scraper provides CLI commands to manage Scrapy configurations:

```bash
# Initialize a new configuration file
scraper scrapy init example-site
```

## Configuration Structure

```yaml
selectors:
  index_page: # How to scrape listing pages
    items:
      item_selector: # How to find resource links
        selector: ".list-item"
        attribute: "href"
        pattern: "regex_pattern" # Optional URL validation pattern
    next_page: # How to find the next page link
      selector: ".next-page"
      attribute: "href"

  resource_page: # How to scrape content pages
    items:
      item_selector: # Container for each content item
        selector: ".content"
      title: # Content fields to extract
        selector: "h1"
      author:
        selector: ".author"
      date:
        selector: ".date"
      content:
        selector: ".post-content"
    next_page: # Pagination within resource pages
      selector: ".next-page"
      attribute: "href"
```

## Field Configuration Options

- `selector`: CSS selector to locate elements
- `attribute`: HTML attribute to extract (optional, defaults to text content)
- `multiple`: Whether to expect multiple elements (default: false)
- `pattern`: Regex pattern for content validation/extraction (optional)

For detailed scraping implementation, see the `BaseSpider` and related classes in the main codebase.
