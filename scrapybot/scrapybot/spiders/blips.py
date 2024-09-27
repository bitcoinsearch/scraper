import json
from datetime import datetime

from bs4 import BeautifulSoup
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from .utils import get_details, strip_tags, strip_attributes, convert_to_iso_datetime


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
        soup = BeautifulSoup(response.text, "html.parser")
        script_tags = soup.find_all("script")
        res = script_tags[-1]
        json_object = json.loads(res.contents[0])
        payload = json_object["payload"]
        article = payload["blob"]["richText"]
        details = BeautifulSoup(article, "html.parser").find("code").text
        details = details.split("\n")
        blip_info = get_details(details[:-1])
        item["id"] = f"blips-{blip_info['bLIP']}"
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
