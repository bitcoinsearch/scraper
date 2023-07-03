from bs4 import BeautifulSoup
import json
import re
import requests
from datetime import datetime

def get_github_urls(base_url: str) -> list:
    """
    get a list of urls 
    """

    urls = []
    for chapter in chapters:
        urls.append(base_url + chapter)

    return urls



def parse_chapters(urls):

    for url in urls:
        data = requests.get(url).text
        soup = BeautifulSoup(data,'html.parser')
        document = {}
        title = soup.find('h2', dir='auto').get_text()
        body = soup.find('div',id = 'readme').get_text()
        body_type = "md"
        author = "Andreas Antonopoulous"
        chapter_number = ''.join(re.findall(r'\d+', url))
        id = "bitcoinbook-chapter-" + chapter_number
        tags = ""
        domain = "https://github.com"
        url = url
        created_at = "2022-11-15" # date of most recent commit

        document.update({
            "title": title,
            "body": body,
            "body_type": body_type,
            "author": author,
            "id": id,
            "tags": tags,
            "domain": domain,
            "url": url,
            "created_at": created_at,
            "indexed_at": datetime.utcnow().isoformat()
            })
        print(document.get("id"))
        documents.append(document)

if __name__ == "__main__":

    documents = []

    chapters = ['/ch01.asciidoc','/ch02.asciidoc','/ch03.asciidoc','/ch04.asciidoc',
            '/ch05.asciidoc','/ch06.asciidoc','/ch07.asciidoc','/ch08.asciidoc',
            '/ch09.asciidoc','/ch10.asciidoc','/ch11.asciidoc','/ch12.asciidoc']

    site = 'https://github.com/bitcoinbook/bitcoinbook/blob/develop'
    print("Getting links for bitcoin book")
    chapter_links = get_github_urls(site)
    parse_chapters(chapter_links)
    print ("Number of documents: " + str(len(documents)))

    with open("bitcoinbook.json", "w") as f:
      json.dump(documents, f, indent=4)

    # Close the file
    f.close()

