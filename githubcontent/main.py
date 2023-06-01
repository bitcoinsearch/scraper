from bs4 import BeautifulSoup
import json
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
            
        print(urls[-5:])
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
            body_type = "raw"
            authors = ["Andreas Antonopoulos"] if is_bitcoin_url else ["Andreas Antonopoulos","Olaoluwa Osuntokun","Rene Pickhardt"]
            id = str(uuid.uuid4())
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

    def parse_bips(self):

        documents = []
        base_url = 'https://github.com/bitcoin/bips'
        
        data = requests.get(base_url).text
        soup = BeautifulSoup(data,'html.parser')
        table = soup.find('table')
        links = table.find_all('a')
        urls = [link['href'] for link in links]
        for url in urls[:3]:
            bip_url = 'https://github.com' + url
            print(bip_url)
            data = requests.get(bip_url).text
            soup = BeautifulSoup(data,'html.parser')
            body = soup.find('article').get_text()
            pattern = r"Comments-URI"
            details = soup.find_all(text=re.compile(pattern))
            bip = details[0]
            domain = "https://github.com"
            url = url
            items = bip.split('\n')
            bip_info = self.get_details(items[:-1])
            document = {}
            document.update({
                "title": bip_info.get("Title"),
                "body": body,
                "body_type": "mediawiki",
                "author": bip_info.get("Author"),
                "id": str(uuid.uuid4()),
                "domain": domain,
                "url": url,
                "created_at": bip_info.get("Created")
                })

            documents.append(document)
        return documents


    def parse_grokking_bitcoin(self):

        base_url = 'https://github.com/kallerosenbaum/grokkingbitcoin/blob/master/grokking-bitcoin.adoc'
        documents = []
        
        data = requests.get(base_url).text
        soup = BeautifulSoup(data,'html.parser')
        content = soup.find('article')
        links = content.find_all('a')
        urls = [link['href'] for link in links]
        for url in urls[1:]:
            doc_url = 'https://github.com' + url
            print(doc_url)
            data = requests.get(doc_url).text
            soup = BeautifulSoup(data,'html.parser')
            article = soup.find('article')
            title = article.find('h2', dir='auto').get_text()
            body = article.get_text()
            print(body)

            document = {}
            document.update({
                "title": title,
                "body": body,
                "body_type": "adoc",
                "authors": ['Kalle Rosenbaum'],
                "id": str(uuid.uuid4()),
                "domain": 'https://github.com',
                "url": url,
                "created_at": "2022-09-14"
                })
            documents.append(document)
        return documents

    def parse_lightning_docs(self):

        base_url = 'https://github.com/t-bast/lightning-docs'
        documents = []
        data = requests.get(base_url).text
        soup = BeautifulSoup(data,'html.parser')
        content = soup.find('article')
        links = content.find_all('a')
        urls = [link['href'] for link in links]
        for url in urls[1:]:
            doc_url = 'https://github.com' + url
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
                "id": str(uuid.uuid4()),
                "domain": 'https://github.com',
                "url": url,
                "created_at": "2022-08-11"
                })
            documents.append(document)
        return documents


    def parse_blips(self):

        documents = []
        base_url = 'https://github.com/lightning/blips'
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
            blip_info = self.get_details(details[:-1])
            document = {}
            document.update({
                "title": blip_info.get("Title"),
                "body": body,
                "body_type": "md",
                "author": blip_info.get("Author"),
                "id": str(uuid.uuid4()),
                "domain": 'https://github.com',
                "url": url,
                "created_at": blip_info.get("Created")
                })

            documents.append(document)
        return documents

    def parse_programming_bitcoin(self):
        chapters = []
        for i in range(1,15):
            number = '0' + str(i) if i < 10 else str(i)
            chapters.append(number)

        base_url = 'https://github.com/jimmysong/programmingbitcoin/blob/master/ch{}.asciidoc'
        print("Getting links for programming bitcoin book")
        chapter_links = get_github_urls(base_url,chapters)
        documents = []
        for url in chapter_links:
            data = requests.get(url).text
            soup = BeautifulSoup(data,'html.parser')
            document = {}
            title = soup.find('h2', dir='auto').get_text()
            body = soup.find('article').get_text()
            body_type = "raw"
            author = "Jimmy Song"
            id = str(uuid.uuid4())
            domain = "https://github.com"
            url = url
            created_at = "2020-12-04"

            document.update({
                "title": title,
                "body": body,
                "body_type": body_type,
                "author": author,
                "id": id,
                "domain": domain,
                "url": url,
                "created_at": created_at
                })
            print(document.get("body"))
            documents.append(document)

        print ("Number of documents: " + str(len(documents)))

        with open("programmingbitcoin.json", "w") as f:
          json.dump(documents, f, indent=4)

        # Close the file
        f.close()

    def parse_btcphilosophy_book(self):
        chapters = ['adversarial-thinking','appendix-discussion','btcphilosophy','build','decentralization',
                    'finite-supply','open-source','privacy','readme', 'review','scaling',
                 'trustlessness','upgrading','when-shit-hits-the-fan' ]

        base_url = 'https://github.com/bitcoin-dev-philosophy/btcphilosophy/blob/master/{}.adoc'
        print("Getting links for bitcoin development philosophy")
        links = get_github_urls(base_url,chapters)
        for link in links[:2]:
            data = requests.get(link).text
            soup = BeautifulSoup(data,'html.parser')
            body = soup.find('article').get_text()
            print(body)

    def get_bitcoinbook_data(self):
        chapters = []
        for i in range(1,13):
            number = '0' + str(i) if i < 10 else str(i)
            chapters.append(number)

        base_url = 'https://github.com/bitcoinbook/bitcoinbook/blob/develop/ch{}.asciidoc'
        print("Getting links for bitcoin book")
        chapter_links = get_github_urls(base_url,chapters)
        bitcoindocs = parse_aantonop_books(chapter_links)
        print ("Number of documents: " + str(len(bitcoindocs)))

        with open("bitcoinbook.json", "w") as f:
          json.dump(bitcoindocs, f, indent=4)
        # Close the file
        f.close()

    def get_bolts(self):
        documents = []
        bolts = ['00-introduction','01-messaging','02-peer-protocol','03-transactions','04-onion-routing',
                    '05-onchain','07-routing-gossip','08-transport',
                    '09-features','10-dns-bootstrap','11-payment-encoding'
                    ]

        base_url = 'https://github.com/lightning/bolts/blob/master/{}.md'
        print("Getting links for lightning bolts")
        bolt_links = self.get_github_urls(base_url,bolts)
        for link in bolt_links:
            data = requests.get(link).text
            soup = BeautifulSoup(data,'html.parser')
            title = soup.find('h1',dir='auto').get_text()
            body = soup.find('article').get_text()
            body_type = "md"
            authors = []
            id = str(uuid.uuid4())
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
            documents.append(document)
        return documents

    def get_lightningbook_data(self):
        chapters = ['01_introduction','02_getting_started','03_how_ln_works','04_node_client',
                    '05_node_operations','06_lightning_architecture','07_payment_channels','08_routing_htlcs',
                    '09_channel_operation','10_onion_routing','11_gossip_channel_graph','12_path_finding','13_wire_protocol',
                    '14_encrypted_transport','15_payment_requests','16_security_privacy_ln','17_conclusion']

        base_url = 'https://github.com/lnbook/lnbook/blob/develop/{}.asciidoc'
        print("Getting links for lightning book")
        chapter_links = get_github_urls(base_url,chapters)
        lndocs = parse_aantonop_books(chapter_links)
        print ("Number of documents: " + str(len(lndocs)))

        with open("lnbook.json", "w") as f:
          json.dump(lndocs, f, indent=4)

        # Close the file
        f.close()

if __name__ == "__main__":

    my_obj = GithubScraper()
    docs = my_obj.get_bolts()
    print(docs)
