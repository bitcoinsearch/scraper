# Scrapy Spider Configurations

This directory contains YAML configuration files that define how spiders scrape specific websites. Each spider follows a three-level pattern:

1. **Index Pages**: Pages that list multiple resources (e.g., blog listing, forum board)
2. **Resource Pages**: Individual pages containing content (e.g., blog post, forum thread)
3. **Items**: The actual content units within pages (e.g., post content, comments)

## Getting Started

### Prerequisites

Before creating a configuration, add your source to `sources.yaml` under the `web` section:

```yaml
web:
  - name: ExampleSite
    domain: example.com
    url: https://example.com/blog
    analyzer_config: # Required for AI-assisted configuration
      index_url: https://example.com/blog
      resource_url: https://example.com/blog/post-1
```

### Creating Your Configuration

You have two options for creating a spider configuration:

#### Option 1: AI-Assisted Configuration

Best for quick setup or complex websites.

```bash
# Generate configuration using AI analysis
scraper scrapy analyze example-site

# Verify the generated configuration
scraper scrapy validate example-site
```

#### Option 2: Manual Configuration

Best for specific requirements or custom scraping behavior.

```bash
# Create a blank configuration file
scraper scrapy init example-site

# Add your selectors (see Configuration Structure below)
# Then verify your configuration
scraper scrapy validate example-site
```

## Configuration Structure

Your YAML configuration should follow this structure:

```yaml
selectors:
  # How to scrape listing pages
  index_page:
    items:
      item_selector:  # How to find resource links
        selector: ".post-link"
        attribute: "href"
        pattern: "/blog/\d+"  # Optional URL pattern
    next_page:  # How to find the next page link
      selector: ".pagination .next"
      attribute: "href"

  # How to scrape content pages
  resource_page:
    items:
      item_selector:  # Container for each content item
        selector: "article.post"
        multiple: true  # true for multiple items (e.g., posts in a thread)
      title:
        selector: "h1.title"
      author:
        selector: ".author-name"
      date:
        selector: "time.published"
      content:
        selector: ".post-content"
      url:
        selector: "link[rel=canonical]"
        attribute: "href"
    next_page:  # For paginated content
      selector: ".load-more"
      attribute: "href"
```

### Selector Options

Each selector can have these properties:

- `selector`: CSS selector to locate elements
- `attribute`: HTML attribute to extract (optional, defaults to text content)
- `multiple`: Whether to expect multiple elements (default: false)
- `pattern`: Regex pattern for validation/extraction (optional)

## Validation

The `validate` command tests your configuration against live pages:

```bash
scraper scrapy validate example-site
```

This will:

- Test all selectors against live pages
- Follow pagination chains
- Extract sample content
- Generate a detailed report

Example validation output:

```
ExampleSite Configuration Validation (✓)
├── Index Page (✓)
│   ├── Items Selector (.post-link) [12 items found]
│   │   ├── Link Pattern (✓): "All URLs match /blog/\d+"
│   │   └── Sample: "https://example.com/blog/123"
│   └── Pagination (✓)
│       └── Chain: 3 pages validated
├── Resource Page (✓)
│   ├── Items (✓)
│   │   ├── Title (✓): "Example Post Title"
│   │   ├── Author (✓): "John Doe"
│   │   ├── Date (✓): "2024-03-13"
│   │   └── Content (✓): "First 100 characters..."
│   └── Pagination (✓)
│       └── Next link found and valid
```

For more details on implementation, see the `BaseSpider` and related classes in the main codebase.
