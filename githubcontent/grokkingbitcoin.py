from bs4 import BeautifulSoup
import requests
import uuid
import json

def parse_grokking_bitcoin():

    base_url = 'https://github.com/kallerosenbaum/grokkingbitcoin/blob/master/grokking-bitcoin.adoc'
    documents = []
    domain =  'https://github.com'
    print("Getting links for grokking bitcoin book")
    data = requests.get(base_url).text
    soup = BeautifulSoup(data,'html.parser')
    content = soup.find('article')
    links = content.find_all('a')
    urls = [link['href'] for link in links]
    for url in urls[1:]:
        doc_url = 'https://github.com' + url
        data = requests.get(doc_url).text
        soup = BeautifulSoup(data,'html.parser')
        article = soup.find('article')
        title = article.find('h2', dir='auto').get_text()
        body = article.get_text()
        document = {}
        document.update({
            "title": title,
            "body": body,
            "body_type": "adoc",
            "authors": ['Kalle Rosenbaum'],
            "id": 'grokkingbitcoin-' + str(uuid.uuid4()),
            "domain":domain,
            "url": domain + url,
            "created_at": "2022-09-14"
            })
        print(document.get("id"))
        documents.append(document)

    print ("Number of documents: " + str(len(documents)))

    with open("grokkingbitcoin.json", "w") as f:
      json.dump(documents, f, indent=4)

    # Close the file
    f.close()


if __name__ == "__main__":

  parse_grokking_bitcoin()
