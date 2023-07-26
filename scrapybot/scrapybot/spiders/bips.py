import re
from bs4 import BeautifulSoup
import json
from datetime import datetime
from .utils import strip_tags, strip_attributes, convert_to_iso_datetime
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

        soup = BeautifulSoup(response.text, "html.parser")
        script_tags = soup.find_all("script")
        res = script_tags[-1]
        json_object = json.loads(res.contents[0])
        payload = json_object["payload"]
        body_to_be_parsed = payload["blob"]["richText"]
        bip_details = BeautifulSoup(body_to_be_parsed, "html.parser").find("pre").text
        metadata = self.parse_details(bip_details)
        item["id"] = "bips-" + str(uuid.uuid4())
        item["title"] = metadata.get("Title")[0]

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
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
                    print(line)
                    line = re.sub(r"<[^>]+>", "", line)
                    data_dict[current_key].append(line.strip())

        return data_dict
