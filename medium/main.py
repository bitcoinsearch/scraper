from trafilatura.sitemaps import sitemap_search
from trafilatura import fetch_url
from trafilatura import extract
import xml.etree.ElementTree as ET
import json

def get_urls_from_sitemap(resource_url: str) -> list:
    """
    get a list of urls from a sitemap with trafilatura
    """
    urls = sitemap_search(resource_url)
    return urls


def parse_articles(urls):
    for url in urls[1:]:
        article = fetch_url(url)
        xml_text = extract(article, output_format='xml')

        root = ET.fromstring(xml_text)

        attribute = root.attrib
        document = {
            "title": attribute.get("title"),
            "body": attribute.get("excerpt"),
            "body_type": "raw",
            "author": attribute.get("author"),
            "id": attribute.get("fingerprint"),
            "tags": attribute.get("tags"),
            "domain": attribute.get("hostname"),
            "url": attribute.get("source"),
            "created_at": attribute.get("date"),
            "type": "article"
        }
        print(document.get("author"))
        documents.append(document)

if __name__ == "__main__":

    documents = []
    pages = ['https://jimmysong.medium.com','https://nopara73.medium.com']

    for page in pages:
        print(f"Getting links for {page}")
        article_links = get_urls_from_sitemap(page)
        parse_articles(article_links)

    print ("Number of documents: " + str(len(documents)))

    with open("medium_articles.json", "w") as f:
      json.dump(documents, f, indent=4)

    # Close the file
    f.close()

