import json
import re
from datetime import datetime

from bs4 import BeautifulSoup
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from .utils import strip_tags, strip_attributes, convert_to_iso_datetime


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
        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = soup.find("script", {"data-target": "react-app.embeddedData"})
        script_tag_content = script_tag.contents[0]
        json_object = json.loads(str(script_tag_content))
        body_to_be_parsed = json_object.get('payload').get('blob').get('richText')
        bip_details = BeautifulSoup(body_to_be_parsed, "html.parser").find("pre").text
        metadata = self.parse_details(bip_details)
        item["id"] = f"bips-{self.parse_id(bip_details)}"
        item["title"] = metadata.get("Title")[0]

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed).strip()
        item["body_type"] = "html"
        item["authors"] = metadata.get("Author")
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = convert_to_iso_datetime(metadata.get("Created")[0])
        item["indexed_at"] = datetime.utcnow().isoformat()
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
                    # logger.info(line)
                    line = re.sub(r"<[^>]+>", "", line)
                    data_dict[current_key].append(line.strip())

        return data_dict

    def parse_id(self, details):
        bip_match = re.search(r'BIP:\s*(\d+)', details)

        bip_value = None
        if bip_match:
            bip_value = bip_match.group(1)

        return bip_value
