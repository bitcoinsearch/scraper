from datetime import datetime
from bs4 import BeautifulSoup
import json
from .utils import strip_tags, strip_attributes
from scrapy.exceptions import DropItem
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class GrokkingbtcSpider(CrawlSpider):
    name = "onboardingtobitcoincore"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/chaincodelabs/onboarding-to-bitcoin-core"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//span/a[contains(@href, 'adoc')]"),
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
        item["id"] = "onboardingtobitcoincore-" + str(uuid.uuid4())

        soup = BeautifulSoup(article, "html.parser")
        header = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

        if header:
            item["title"] = "[Onboarding to Bitcoin Core] " + header.text
        else:
            item["title"] = "[Onboarding to Bitcoin Core]"
        
        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(article)
        item["body"] = strip_tags(article)
        item["body_type"] = "html"
        item["authors"] = ["Will Clark"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = datetime.utcnow().isoformat()
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
