import uuid
from datetime import datetime
import re
from .utils import strip_tags, strip_attributes
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class RustySpider(CrawlSpider):
    name = "rusty"
    allowed_domains = ["rusty.ozlabs.org"]
    start_urls = ["https://rusty.ozlabs.org"]

    rules = (Rule(LinkExtractor(), callback="parse_item", follow=True),)

    def parse_item(self, response):
        item = {}
        keywords = ["bitcoin", "lightning", "bip", "payment", "block", "transaction"]
        article = response.xpath('//div[@class="entry-content"]').get()
        item["id"] = "rusty-blog-" + str(uuid.uuid4())
        item["title"] = response.xpath("//h1/text()").get()
        item["body"] = strip_tags(article)
        item["body_formatted"] = strip_attributes(article)
        item["body_type"] = "html"
        item["authors"] = [
            response.xpath('//span[@class="author vcard"]/a/text()').get()
        ]
        item["domain"] = 'https://' + self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = response.xpath(
            '//time[@class="entry-date published"]/@datetime'
        ).get()

        if not item["created_at"]:
            item["created_at"] = datetime.now()

        item["indexed_at"] = datetime.utcnow().isoformat()
        pattern = re.compile("|".join(keywords), re.IGNORECASE)

        if item["title"] and re.search(pattern, item["title"]):
            return item

        return None
