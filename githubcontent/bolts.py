from bs4 import BeautifulSoup
import requests
import uuid
import json

from utils import GithubScraper
scraper = GithubScraper()

def get_bolts():
    documents = []
    bolts = ['00-introduction','01-messaging','02-peer-protocol','03-transactions','04-onion-routing',
                '05-onchain','07-routing-gossip','08-transport',
                '09-features','10-dns-bootstrap','11-payment-encoding'
                ]

    base_url = 'https://github.com/lightning/bolts/blob/master/{}.md'
    print("Getting links for lightning bolts")
    bolt_links = scraper.get_github_urls(base_url,bolts)
    for link in bolt_links:
        data = requests.get(link).text
        soup = BeautifulSoup(data,'html.parser')
        title = soup.find('h1',dir='auto').get_text()
        body = soup.find('article').get_text()
        body_type = "md"
        authors = []
        id = 'bolts-' + str(uuid.uuid4())
        url = link
        domain = "https://github.com"
        created_at = "2023-05-11"
        document = {}

        document.update({
            "title": title,
            "body": body,
            "body_type": body_type,
            "authors": authors,
            "id": id,
            "domain": domain,
            "url": url,
            "created_at": created_at
            })
        print(document.get("id"))
        documents.append(document)
    print ("Number of documents: " + str(len(documents)))

    with open("bolts.json", "w") as f:
      json.dump(documents, f, indent=4)

    # Close the file
    f.close()

if __name__ == "__main__":

  get_bolts()
