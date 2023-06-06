import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class RiverSpider(CrawlSpider):
    name = "river"
    allowed_domains = ["river.com"]
    start_urls = ["https://river.com"]

    rules = (Rule(LinkExtractor(allow=r"terms"), callback="parse_item", follow=True),)

    def parse_item(self, response):
        clearn = response.xpath('//div[@class="c-learn__content"]')
        item = {}
        item["url"] = response.url
        item['title'] = clearn.xpath('//h1/text()').get()
        item['body'] = clearn.xpath('//div[@class="c-article"]/p').getall()
        #item["domain_id"] = response.xpath('//input[@id="sid"]/@value').get()
        #item["name"] = response.xpath('//div[@id="name"]').get()
        #item["description"] = response.xpath('//div[@id="description"]').get()
        return item
