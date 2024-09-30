from .base import BaseScraper


class WebScraper(BaseScraper):
    async def scrape(self, index_name: str):
        raise NotImplementedError("Web scraping is not implemented yet")
