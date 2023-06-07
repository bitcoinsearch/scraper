from .utils import strip_tags
from datetime import datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class LearnmeabitcoinSpider(CrawlSpider):
    name = "learnmeabitcoin"
    allowed_domains = ["learnmeabitcoin.com"]
    start_urls = ["https://learnmeabitcoin.com"]

    rules = (
        Rule(
            LinkExtractor(allow=[r"beginners", r"technical"]),
            callback="parse_item",
            follow=True,
        ),
    )

    def parse_item(self, response):
        item = {}

        article = response.xpath("//article/div/p").getall()  # returns a list
        body_to_be_parsed = "".join(article)  # turn list of paragraphs to one string
        item["id"] = "learnmeabitcoin-" + str(uuid.uuid4())
        item["title"] = response.xpath("//header/h1/text()").get()
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "raw"
        item["authors"] = ["Gregory Walker"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = datetime.now()

        return item
