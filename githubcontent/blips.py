from bs4 import BeautifulSoup
import re
import requests
import uuid
import json
from utils import GithubScraper

scraper = GithubScraper()

def parse_blips():

    documents = []
    base_url = 'https://github.com/lightning/blips'
    domain =  'https://github.com'
    data = requests.get(base_url).text
    soup = BeautifulSoup(data,'html.parser')
    table = soup.find('table')
    links = table.find_all('a')
    urls = [link['href'] for link in links]
    for url in urls:
        doc_url = 'https://github.com' + url
        data = requests.get(doc_url).text
        soup = BeautifulSoup(data,'html.parser')
        body = soup.find('article').get_text()
        details = soup.find(class_='notranslate').get_text()
        details = details.split("\n")
        blip_info = scraper.get_details(details[:-1])
        document = {}
        document.update({
            "title": blip_info.get("Title"),
            "body": body,
            "body_type": "md",
            "authors": [blip_info.get("Author")],
            "id": 'blips' + str(uuid.uuid4()),
            "domain": domain,
            "url": doc_url,
            "created_at": blip_info.get("Created")
            })
        print(document.get("id"))
        documents.append(document)
    print ("Number of documents: " + str(len(documents)))

    with open("blips.json", "w") as f:
      json.dump(documents, f, indent=4)

    # Close the file
    f.close()

if __name__ == "__main__":

  parse_blips()
