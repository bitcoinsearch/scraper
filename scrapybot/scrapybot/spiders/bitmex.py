import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BitmexSpider(CrawlSpider):
    name = "bitmex"
    allowed_domains = ["blog.bitmex.com"]
    start_urls = ["https://blog.bitmex.com/category/research/?lang=en_us"]

    rules = (Rule(LinkExtractor(), callback="parse_item", follow=True),)

    def parse_item(self, response):
        item = {}
        item["url"] = response.url
        #item["domain_id"] = response.xpath('//input[@id="sid"]/@value').get()
        #item["name"] = response.xpath('//div[@id="name"]').get()
        #item["description"] = response.xpath('//div[@id="description"]').get()
        return item
