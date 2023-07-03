from datetime import datetime
from .utils import strip_tags, strip_attributes
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BitmexSpider(CrawlSpider):
    name = "bitmex"
    allowed_domains = ["blog.bitmex.com"]
    start_urls = ["https://blog.bitmex.com/category/research/?lang=en_us"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths='//td[@class="item-details"]/h3/a'),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}
        article = response.xpath("//article/div/p").getall()
        body_to_be_parsed = "".join(article)  # turn list of paragraphs to one string

        item["id"] = "bitmex-blog-" + str(uuid.uuid4())
        item["title"] = response.xpath('//h1[@class="entry-title"]/text()').get()
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "html"
        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["authors"] = [
            response.xpath('//div[@class="td-post-author-name"]/a/text()').get()
        ]
        item["domain"] = "https://" + self.allowed_domains[0]
        item["url"] = response.url
        item["created_at"] = response.xpath(
            '//span[@class="td-post-date"]/time/@datetime'
        ).get()
        item["indexed_at"] = datetime.utcnow().isoformat()
        return item
