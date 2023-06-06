import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class NakamotoinstituteSpider(CrawlSpider):
    name = "nakamotoinstitute"
    allowed_domains = ["satoshi.nakamotoinstitute.org","nakamotoinstitute.org"]
    start_urls = ["https://satoshi.nakamotoinstitute.org"]

    rules = (Rule(LinkExtractor(deny=[r"bitcointalk",r"research"]), callback="parse_item", follow=True),)

    def parse_item(self, response):
        item = {}
        item["url"] = response.url
        item["body"] = response.xpath('//div[@class="container"]').get()
        #item["description"] = response.xpath('//div[@id="description"]').get()
        return item
