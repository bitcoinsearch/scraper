import re
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class MediumSpider(CrawlSpider):
    name = "medium"
    allowed_domains = ["medium.com"]
    start_urls = ["https://medium.com/@nassersaazi"]

    rules = (
        Rule(LinkExtractor(allow=[r"nassersaazi"]), callback="parse_item", follow=True),
    )

    def parse_item(self, response):
        item = {}
        item["url"] = response.url
        # item["domain_id"] = response.xpath('//input[@id="sid"]/@value').get()
        # item["name"] = response.xpath('//div[@id="name"]').get()
        # item["description"] = response.xpath('//div[@id="description"]').get()
        return item
