import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BitcoinmagazineSpider(CrawlSpider):
    name = "bitcoinmagazine"
    allowed_domains = ["bitcoinmagazine.com"]
    start_urls = ["https://bitcoinmagazine.com"]

    rules = (
        Rule(
            LinkExtractor(allow=r"aaron-van-wirdum"), callback="parse_item", follow=True
        ),
    )

    def parse_item(self, response):
        item = {}
        item["url"] = response.url
        # item["domain_id"] = response.xpath('//input[@id="sid"]/@value').get()
        # item["name"] = response.xpath('//div[@id="name"]').get()
        # item["description"] = response.xpath('//div[@id="description"]').get()
        return item
