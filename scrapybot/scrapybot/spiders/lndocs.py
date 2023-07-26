from .utils import strip_tags, strip_attributes
from bs4 import BeautifulSoup
import json
from datetime import datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class LndocsSpider(CrawlSpider):
    name = "lndocs"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/t-bast/lightning-docs"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//article/ul/li/a"),
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

        item["id"] = "lndocs-" + str(uuid.uuid4())

        item["title"] = (
            "[Lightning-docs ] "
            + BeautifulSoup(article, "html.parser")
            .find(["h1", "h2", "h3", "h4", "h5", "h6"])
            .text
        )

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(article)
        item["body"] = strip_tags(article)
        item["body_type"] = "raw"
        item["authors"] = ["Bastien Teinturier"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = datetime.utcnow().isoformat()
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
