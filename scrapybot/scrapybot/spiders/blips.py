from datetime import datetime

from .utils import get_details, strip_tags, strip_attributes, convert_to_iso_datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BlipsSpider(CrawlSpider):
    name = "blips"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/lightning/blips"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//table/tbody/tr/td/a"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}
        details = response.xpath(
            "//pre[contains(@class, 'notranslate')]/code/text()"
        ).get()
        details = details.split("\n")
        article = response.xpath("//article").get()
        blip_info = get_details(details[:-1])
        item["id"] = "blips-" + str(uuid.uuid4())
        item["title"] = blip_info.get("Title")

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(article)
        item["body"] = strip_tags(article)
        item["body_type"] = "html"
        item["authors"] = [blip_info.get("Author")]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = convert_to_iso_datetime(blip_info.get("Created"))
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
