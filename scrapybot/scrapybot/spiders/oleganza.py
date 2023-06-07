from .utils import strip_tags
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

        body = response.xpath('//div[@id="content"]')
        post = body.xpath('//div[@class="regular"]').get()
        item["id"] = "oleganza-blog-" + str(uuid.uuid4())
        item["title"] = body.xpath('//div[@class="regular"]/h2/a/text()').get()
        item["body"] = strip_tags(post)
        item["body_type"] = "raw"
        item["authors"] = [body.xpath("//h1/a/text()").get()]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = body.xpath('//div[@class="date"]/a/text()').get()

        return item
