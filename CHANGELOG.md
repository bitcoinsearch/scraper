## 0.2.0 (2025-01-09)

### Feat

- add github actions workflows for scraperv2
- **github**: add `checkout_commit` option for testing specific repo states
- **scrapers**: Add GitHub metadata scraper for issues and pull requests
- **elastic**: add index mappings and initialization commands
- **scrapers**: stackexchange api scraper (#90)
- **scrapers**: add Bitcoin Core PR Review Club
- **github**: add repository metadata field analyzer
- **scrapy**: add LLM analyzer and config validation
- **scrapy**: implement configuration-based system
- **notebooks**: add summary efficiency analysis notebook
- **scrapers**: add flexible scrapy-based scraper
- **data**: add structured author information with aliases
- **processors**: implement flexible document processing pipeline
- **scraper**: introduce scraping package

### Fix

- **bitcointalk**: add missing configuration file
- resolve ModuleNotFoundError for common - Added sys.path modification to include the repository root directory
- import error for 6922e937
- UTC `indexed_at` timestamp

### Refactor

- **scrapers**: standardize markdown as canonical format
- **logging**: migrate from MetadataDocument to ScraperRunDocument
- **pr-review-club**: follow existing schema
- **elasticsearch**: support for local instance (#82)
