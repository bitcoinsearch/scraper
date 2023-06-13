import uuid
from scrapy.exceptions import DropItem
from .utils import strip_tags
from datetime import datetime
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BtcphilosophySpider(CrawlSpider):
    name = "btcphilosophy"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/bitcoin-dev-philosophy/btcphilosophy"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//span/a[contains(@href, 'adoc')]"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}
        article = response.xpath("//article").get()
        item["id"] = "btcphilosophy-" + str(uuid.uuid4())
        item["title"] = response.xpath("//article/div/h2/text()").get()
        item["body_formatted"] = article
        item["body"] = strip_tags(article)
        item["body_type"] = "adoc"
        item["authors"] = ["Kalle Rosenbaum", "Linnéa Rosenbaum"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = str(datetime.now())

        if not item["title"]:
            raise DropItem("Title not in document")

        return item
