from .utils import strip_tags
from datetime import datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class LndocsSpider(CrawlSpider):
    name = "lndocs"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/t-bast/lightning-docs"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//article/ul/li/a"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}
        article = response.xpath("//article").get()
        item["id"] = "lndocs-" + str(uuid.uuid4())
        item["title"] = response.xpath("//article/h1/text()").get()
        item["body_formatted"] = article
        item["body"] = strip_tags(article)
        item["body_type"] = "raw"
        item["authors"] = ["Bastien Teinturier"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = str(datetime.now())

        return item
