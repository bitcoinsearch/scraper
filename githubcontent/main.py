from bs4 import BeautifulSoup
import json
import re
import requests
import uuid

def get_github_urls(base_url: str, chapters: list) -> list:
    """
    get a list of urls 
    """
    urls = []
    for chapter in chapters:
        urls.append(base_url.format(chapter))
        
    print(urls[-5:])
    return urls

def parse_aantonop_books(urls):

    documents = []
    for url in urls:
        is_bitcoin_url = re.search('bitcoinbook', url)
        data = requests.get(url).text
        soup = BeautifulSoup(data,'html.parser')
        document = {}
        title = soup.find('h2', dir='auto').get_text()
        body = soup.find('div',id = 'readme').get_text()
        body_type = "raw"
        authors = ["Andreas M. Antonopoulos"] if is_bitcoin_url else ["Andreas M. Antonopoulos","Olaoluwa Osuntokun","Rene Pickhardt"]
        id = str(uuid.uuid4())
        domain = "https://github.com"
        url = url
        created_at = "2022-11-15" if is_bitcoin_url else "2023-04-22"# date of most recent commit

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
        print(document.get("id"))
        documents.append(document)

    return documents

def parse_bips():

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
        print(details)

def parse_programming_bitcoin():
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

def get_bitcoinbook_data():
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

def get_lightningbook_data():
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

    parse_bips()
