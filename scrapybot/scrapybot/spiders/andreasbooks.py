import uuid
from .utils import strip_tags, strip_attributes
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

        article = response.xpath("//div[@id='readme']").get()
        item["id"] = (
            "masteringbitcoin-" + str(uuid.uuid4())
            if "bitcoinbook" in response.url
            else "masteringln-" + str(uuid.uuid4())
        )
        item["title"] = response.xpath("//article/div/h2/text()").get()

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
        item["domain"] = self.allowed_domains[0]
        item["created_at"] = (
            "2022-11-15" if "bitcoinbook" in response.url else "2023-04-22"
        )  # date of most recent commit
        return item
