from .utils import strip_tags
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
        clearn = response.xpath('//div[@class="c-learn__content"]')
        term = clearn.xpath('//div[@class="c-article"]/p').getall()  # returns a list
        body_to_be_parsed = "".join(term)  # turn list of paragraphs to one string

        item = {}
        item["id"] = "river-glossary-" + str(uuid.uuid4())
        item["title"] = clearn.xpath("//h1/text()").get()
        item["body_formatted"] = body_to_be_parsed
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "raw"
        item["authors"] = []
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = str(datetime.now())

        return item
