from bs4 import BeautifulSoup
import re
import requests
import uuid

class GithubScraper:
    def get_github_urls(self,base_url: str, chapters: list) -> list:
        """
        get a list of urls 
        """
        urls = []
        for chapter in chapters:
            urls.append(base_url.format(chapter))
            
        return urls

    def parse_aantonop_books(self,urls):

        documents = []
        for url in urls:
            is_bitcoin_url = re.search('bitcoinbook', url)
            data = requests.get(url).text
            soup = BeautifulSoup(data,'html.parser')
            document = {}
            title = soup.find('h2', dir='auto').get_text()
            body = soup.find('div',id = 'readme').get_text()
            body_type = "asciidoc"
            authors = ["Andreas Antonopoulos"] if is_bitcoin_url else ["Andreas Antonopoulos","Olaoluwa Osuntokun","Rene Pickhardt"]
            id = 'masteringbitcoin' + str(uuid.uuid4()) if is_bitcoin_url else 'masteringln' + str(uuid.uuid4())
            domain = "https://github.com"
            url = url
            created_at = "2022-11-15" if is_bitcoin_url else "2023-04-22"# date of most recent commit

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

        return documents

    def get_details(self, details: list):
        result_dict = {}

        for item in details:
            if ': ' in item:
                key, value = item.split(': ', 1)
                result_dict[key.strip()] = value.strip()
            else:
                print(f"Ignoring item: {item}")
        return result_dict


