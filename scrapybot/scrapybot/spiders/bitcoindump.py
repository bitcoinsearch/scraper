from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BitcoindumpSpider(CrawlSpider):
    name = "bitcoindump"
    allowed_domains = ["dump.bitcoin.it"]
    start_urls = ["https://dump.bitcoin.it"]
    # r'\b_en\b'
    rules = (Rule(LinkExtractor(), callback="parse_item", follow=True),)

    def parse_item(self, response):
        item = {}
        item["url"] = response.url
        urls = response.xpath("//a/@href").getall()
        item["urls"] = [s for s in urls if "en" in s]
        # item["domain_id"] = response.xpath('//input[@id="sid"]/@value').get()
        # item["name"] = response.xpath('//div[@id="name"]').get()
        # item["description"] = response.xpath('//div[@id="description"]').get()
        return item
