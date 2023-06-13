import uuid
from .utils import strip_tags
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class RustySpider(CrawlSpider):
    name = "rusty"
    allowed_domains = ["rusty.ozlabs.org"]
    start_urls = ["https://rusty.ozlabs.org"]

    rules = (Rule(LinkExtractor(), callback="parse_item", follow=True),)

    def parse_item(self, response):
        item = {}
        article = response.xpath('//div[@class="entry-content"]').get()
        item["id"] = "rusty-blog-" + str(uuid.uuid4())
        item["title"] = response.xpath("//h1/text()").get()
        item["body_formatted"] = article
        item["body"] = strip_tags(article)
        item["body_type"] = "raw"
        item["authors"] = [
            response.xpath('//span[@class="author vcard"]/a/text()').get()
        ]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = response.xpath(
            '//time[@class="entry-date published"]/@datetime'
        ).get()

        return item
