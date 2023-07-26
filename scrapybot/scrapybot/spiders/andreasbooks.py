import uuid
from bs4 import BeautifulSoup
import json
from .utils import strip_tags, strip_attributes, convert_to_iso_datetime
from datetime import datetime
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class AndreasbooksSpider(CrawlSpider):
    name = "andreasbooks"
    allowed_domains = ["github.com"]
    start_urls = [
        "https://github.com/bitcoinbook/bitcoinbook",
        "https://github.com/lnbook/lnbook",
    ]

    rules = (
        Rule(
            LinkExtractor(
                allow=[r".*\d+.*"], deny=[r"part"], restrict_xpaths="//article/ul/li/a"
            ),
            callback="parse_item",
            follow=True,
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
        item["id"] = (
            "masteringbitcoin-" + str(uuid.uuid4())
            if "bitcoinbook" in response.url
            else "masteringln-" + str(uuid.uuid4())
        )

        item["title"] = (
            "[Mastering Bitcoin] "
            + BeautifulSoup(article, "html.parser").find("h2").text
            if "bitcoinbook" in response.url
            else "[Mastering Lightning] "
            + BeautifulSoup(article, "html.parser").find("h2").text
        )

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(article)
        item["body"] = strip_tags(article)
        item["body_type"] = "html"
        item["url"] = response.url
        item["authors"] = (
            ["Andreas Antonopoulos"]
            if "bitcoinbook" in response.url
            else ["Andreas Antonopoulos", "Olaoluwa Osuntokun", "Rene Pickhardt"]
        )
        item["domain"] = (
            self.start_urls[0] if "bitcoinbook" in response.url else self.start_urls[1]
        )
        item["created_at"] = convert_to_iso_datetime(
            "2022-11-15" if "bitcoinbook" in response.url else "2023-04-22"
        )  # date of most recent commit
        item["indexed_at"] = datetime.utcnow().isoformat()
        return item
