import re
from .utils import strip_tags, strip_attributes
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BipsSpider(CrawlSpider):
    name = "bips"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/bitcoin/bips"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//td/a"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}

        body_to_be_parsed = response.xpath("//article").get()
        bip_details = response.xpath(
            "//*[contains(text(), 'Comments-URI')]/text()"
        ).get()
        metadata = self.parse_details(bip_details)
        response.xpath("//article").get()
        item["id"] = "bips-" + str(uuid.uuid4())
        item["title"] = metadata.get("Title")[0]

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "mediawiki"
        item["authors"] = metadata.get("Author")
        item["domain"] = self.allowed_domains[0]
        item["url"] = response.url
        item["created_at"] = metadata.get("Created")[0]
        return item

    def parse_details(self, details):
        data_lines = details.split("\n")
        data_dict = {}
        current_key = None

        for line in data_lines:
            if line.strip():
                if ":" in line:
                    key, value = line.split(":", 1)
                    current_key = key.strip()
                    if current_key == "Author":
                        # Remove emails from the value
                        value = re.sub(r"<[^>]+>", "", value)
                    data_dict[current_key] = [value.strip()]
                else:
                    print(line)
                    line = re.sub(r"<[^>]+>", "", line)
                    data_dict[current_key].append(line.strip())

        return data_dict
