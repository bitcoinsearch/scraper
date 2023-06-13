import uuid
from .utils import strip_tags
from scrapy.exceptions import DropItem
from datetime import datetime
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class ProgrammingbtcSpider(CrawlSpider):
    name = "programmingbtc"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/jimmysong/programmingbitcoin"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//span/a[contains(@href, 'asciidoc')]"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}
        article = response.xpath("//article").get()
        item["id"] = "programmingbtc-" + str(uuid.uuid4())
        item["title"] = response.xpath("//article/div/h2/text()").get()
        item["body_formatted"] = article
        item["body"] = strip_tags(article)
        item["body_type"] = "asciidoc"
        item["authors"] = ["Jimmy Song"]
        item["domain"] = self.allowed_domains[0]
        item["url"] = response.url
        item["created_at"] = str(datetime.now())

        if not item["title"]:
            raise DropItem("Title not in document")

        return item
