import re
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class RustySpider(CrawlSpider):
    name = "rusty"
    allowed_domains = ["rusty.ozlabs.org"]
    start_urls = ["https://rusty.ozlabs.org"]

    rules = (Rule(LinkExtractor(), callback="parse_item", follow=True),)

    def parse_item(self, response):
        item = {}
        item["url"] = response.url
        article = response.xpath('//article')
        item["title"] = article.xpath('//h1/text()').get()
        unparsedbody = article.xpath('//div[@class="entry-content"]').get()
        item["body"] = self.striphtml(unparsedbody)
        item["created_at"] = article.xpath('//time[@class="entry-date published"]/@datetime').get()
        item["author"] = article.xpath('//span[@class="author vcard"]/a/text()').get()

        return item

    def striphtml(self,data):
        p = re.compile(r'<.*?>')
        return p.sub('', data)
