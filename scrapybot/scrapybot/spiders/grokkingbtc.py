from datetime import datetime
from .utils import strip_tags
from scrapy.exceptions import DropItem
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class GrokkingbtcSpider(CrawlSpider):
    name = "grokkingbtc"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/kallerosenbaum/grokkingbitcoin"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//span/a[contains(@href, 'adoc')]"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}
        article = response.xpath("//article").get()
        item["id"] = "grokkingbtc-" + str(uuid.uuid4())
        item["title"] = response.xpath("//article/div/h2/text()").get()
        item["body_formatted"] = article
        item["body"] = strip_tags(article)
        item["body_type"] = "adoc"
        item["authors"] = ["Kalle Rosenbaum"]
        item["domain"] = self.allowed_domains[0]
        item["url"] = response.url
        item["created_at"] = str(datetime.now())

        if not item["title"]:
            raise DropItem("Title not in document")

        return item
