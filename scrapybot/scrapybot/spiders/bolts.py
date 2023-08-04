import uuid
import json
import re
from bs4 import BeautifulSoup
from .utils import strip_tags, strip_attributes, convert_to_iso_datetime
from datetime import datetime
from .utils import strip_tags
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BoltsSpider(CrawlSpider):
    name = "bolts"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/lightning/bolts"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//span/a[contains(@href, 'md')]"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}
        # Regular expression pattern to match URLs containing numbers
        pattern = r"\d"
        if not re.search(pattern, response.url):
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        script_tags = soup.find_all("script")
        res = script_tags[-1]
        json_object = json.loads(res.contents[0])
        payload = json_object["payload"]
        body_to_be_parsed = payload["blob"]["richText"]
        item["id"] = "bolts-" + str(uuid.uuid4())
        item["title"] = BeautifulSoup(body_to_be_parsed, "html.parser").find("h1").text

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "html"
        item["authors"] = ["Spec"]
        item["domain"] = "https://github.com/lightning/bolts"
        item["created_at"] = convert_to_iso_datetime("2023-05-11")
        item["url"] = response.url
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
