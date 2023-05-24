from .utils import strip_tags, strip_attributes
import re
from datetime import datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class RiverSpider(CrawlSpider):
    name = "river"
    allowed_domains = ["river.com"]
    start_urls = ["https://river.com"]

    rules = (Rule(LinkExtractor(allow=r"terms"), callback="parse_item", follow=True),)

    def parse_item(self, response):
        keywords = [
            "taproot",
            "script",
            "wallet",
            "watchtower",
            "sign",
            "chain",
            "contract",
            "proof",
            "fork",
            "vByte",
            "bitcoin",
            "lightning",
            "bip",
            "payment",
            "block",
            "transaction",
        ]
        clearn = response.xpath('//div[@class="c-learn__content"]')
        term = clearn.xpath('//div[@class="c-article"]/p').getall()  # returns a list
        body_to_be_parsed = "".join(term)  # turn list of paragraphs to one string

        item = {}
        item["id"] = "river-glossary-" + str(uuid.uuid4())
        item["title"] = clearn.xpath("//h1/text()").get()
        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "html"
        item["authors"] = ["river"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = datetime.now()

        pattern = re.compile("|".join(keywords), re.IGNORECASE)

        if item["title"] and re.search(pattern, item["title"]):
            return item

        return None
