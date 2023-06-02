from bs4 import BeautifulSoup
import re
import requests
import uuid
import json
from utils import GithubScraper
scraper = GithubScraper()

def parse_bips():

    documents = []
    base_url = 'https://github.com/bitcoin/bips'
    domain =  'https://github.com'
    data = requests.get(base_url).text
    soup = BeautifulSoup(data,'html.parser')
    table = soup.find('table')
    links = table.find_all('a')
    urls = [link['href'] for link in links]
    for url in urls:
        bip_url = domain + url
        data = requests.get(bip_url).text
        soup = BeautifulSoup(data,'html.parser')
        body = soup.find('article').get_text()
        pattern = r"Comments-URI"
        details = soup.find_all(text=re.compile(pattern))
        bip = details[0]
        domain = domain
        items = bip.split('\n')
        bip_info = scraper.get_details(items[:-1])
        document = {}
        document.update({
            "title": bip_info.get("Title"),
            "body": body,
            "body_type": "mediawiki",
            "authors": [bip_info.get("Author")],
            "id": 'bips-' + str(uuid.uuid4()),
            "domain": domain,
            "url": bip_url,
            "created_at": bip_info.get("Created")
            })
        print(document.get("id"))
        documents.append(document)

    print ("Number of documents: " + str(len(documents)))

    with open("bips.json", "w") as f:
      json.dump(documents, f, indent=4)

    # Close the file
    f.close()

if __name__ == "__main__":

  parse_bips()
