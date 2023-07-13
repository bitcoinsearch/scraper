from .utils import strip_tags, strip_attributes
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

        if not body_to_be_parsed:
            return None

        item["id"] = "learnmeabitcoin-" + str(uuid.uuid4())
        item["title"] = response.xpath("//header/h1/text()").get()

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "html"
        item["authors"] = ["Gregory Walker"]
        item["domain"] = 'https://' + self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = datetime.now()
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
