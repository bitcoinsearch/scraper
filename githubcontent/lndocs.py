from bs4 import BeautifulSoup
import requests
import uuid
import json

def parse_lightning_docs():

    base_url = 'https://github.com/t-bast/lightning-docs'
    domain =  'https://github.com'
    documents = []
    data = requests.get(base_url).text
    soup = BeautifulSoup(data,'html.parser')
    content = soup.find('article')
    links = content.find_all('a')
    urls = [link['href'] for link in links]
    for url in urls[1:]:
        doc_url = domain + url
        data = requests.get(doc_url).text
        soup = BeautifulSoup(data,'html.parser')
        document = {}
        article = soup.find('article')
        body = article.get_text()
        title = article.find('h1').get_text()
        document.update({
            "title": title,
            "body": body,
            "body_type": "md",
            "authors": ['Bastien Teinturier'],
            "id": 'lightningdocs-' + str(uuid.uuid4()),
            "domain":domain,
            "url": doc_url,
            "created_at": "2022-08-11"
            })
        print(document.get("id"))
        documents.append(document)

    print ("Number of documents: " + str(len(documents)))

    with open("lightningdocs.json", "w") as f:
      json.dump(documents, f, indent=4)

    # Close the file
    f.close()

if __name__ == "__main__":

  parse_lightning_docs()
