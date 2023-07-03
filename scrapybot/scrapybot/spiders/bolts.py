import uuid
from .utils import strip_tags, strip_attributes
from datetime import datetime
from .utils import strip_tags
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BoltsSpider(CrawlSpider):
    name = "bolts"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/lightning/bolts/blob/master/00-introduction.md"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//ol/li/a"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}

        body_to_be_parsed = response.xpath("//article").get()
        item["id"] = "bolts-" + str(uuid.uuid4())
        item["title"] = response.xpath('//h1[@dir="auto"]/text()').get()

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "markdown"
        item["authors"] = ["Spec"]
        item["domain"] = "https://github.com/lightning/bolts"
        item["created_at"] = datetime.fromisoformat("2023-05-11")
        item["url"] = response.url
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
