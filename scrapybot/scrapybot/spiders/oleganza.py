from .utils import strip_tags, strip_attributes
from datetime import datetime
import re
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class OleganzaSpider(CrawlSpider):
    name = "oleganza"
    allowed_domains = ["blog.oleganza.com"]
    start_urls = ["https://blog.oleganza.com"]

    rules = (Rule(LinkExtractor(), callback="parse_item", follow=True),)

    def parse_item(self, response):
        item = {}

        keywords = [
            "bitcoin",
            "lightning",
            "bip",
            "payment",
            "block",
            "transaction",
            "money",
            "segwit",
            "hash",
            "crypto",
        ]
        body = response.xpath('//div[@id="content"]')
        post = body.xpath('//div[@class="regular"]').get()
        if not post:
            return None
        item["id"] = "oleganza-blog-" + str(uuid.uuid4())
        item["title"] = body.xpath('//div[@class="regular"]/h2/a/text()').get()
        item["body_formatted"] = strip_attributes(post)
        item["body"] = strip_tags(post)
        item["body_type"] = "html"
        item["authors"] = ["Oleg Andreev"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = datetime.now()
        item["indexed_at"] = datetime.utcnow().isoformat()

        pattern = re.compile("|".join(keywords), re.IGNORECASE)

        if item["title"] and re.search(pattern, item["title"]):
            return item

        return None
