import json
import os
import time
from datetime import datetime

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger
from requests import request

from common.elasticsearch_utils import upsert_document

load_dotenv()

BOARD_URL = 'https://bitcointalk.org/index.php?board=6.'

authors = ['achow101', 'kanzure', 'Sergio_Demian_Lerner', 'Nicolas Dorier', 'jl2012', 'Peter Todd', 'Gavin Andresen',
           'adam3us', 'Pieter Wuille', 'Meni Rosenfeld', 'Mike Hearn', 'wumpus', 'Luke-Jr', 'Matt Corallo', 'jgarzik',
           'andytoshi', 'satoshi', 'Cdecker', 'TimRuffing', 'gmaxwell']


def fetch_all_topics() -> list:
    data_dir = os.getenv('DATA_DIR')
    if not os.path.exists(os.path.join(data_dir, 'bitcointalk')):
        os.makedirs(os.path.join(data_dir, 'bitcointalk'), exist_ok=True)
    offset = 0
    topics = []
    while True:
        logger.info(f"Downloading page {offset // 40}...")
        url = f"{BOARD_URL}{offset}"
        success = False
        tops = []
        while not success:
            response = request('post', url)
            text = response.text
            if response.status_code != 200:
                logger.error(f"Error {response.status_code} downloading page {offset // 20}")
                time.sleep(2)
                continue
            success = True
            soup = BeautifulSoup(text, 'html.parser')
            links = soup.select('tr > td > span > a')
            for link in links:
                href = link.get('href')
                if not href.startswith("https://bitcointalk.org/index.php?topic=") or 'class' in link.attrs:
                    continue
                tops.append(href)
            offset += 40
        topics.extend(tops)
        if len(tops) != 40:
            logger.info("No more data")
            break
        time.sleep(0.8)
        break
    return topics


def get_documents_from_post(url: str) -> dict:
    response = request('get', url)
    text = response.text
    if response.status_code >= 500 or response.status_code == 403:
        logger.error(f"Error {response.status_code} downloading {url}")
        time.sleep(10)
        return get_documents_from_post(url)
    soup = BeautifulSoup(text, 'html.parser')
    urls = list(set([a.get('href') for a in soup.find_all(class_='navPages')]))
    table = soup.select_one('#quickModForm > table:nth-child(1)')
    first_tr_class = table.find('tr').get('class')
    tr_list = table.find_all('tr', class_=first_tr_class)
    logger.info(f"Found {len(tr_list)} posts in {url}")
    documents = []
    for tr in tr_list:
        author = tr.select_one('.poster_info > b > a').text
        if author not in authors:
            continue
        logger.info(f"post by : {author}")
        date = tr.select_one('.td_headerandpost .smalltext > .edited')
        if not date:
            date = tr.select_one('.td_headerandpost .smalltext').text
        else:
            date = date.text
        merited_index = date.find('Merited by')
        if merited_index != -1:
            date = date[:merited_index]
        if date.startswith('Today at'):
            date = date.replace('Today at', datetime.now().strftime('%Y-%m-%d'))
        date = datetime.strptime(date, '%B %d, %Y, %I:%M:%S %p')
        url = tr.select_one('.td_headerandpost .subject > a').get('href')
        title = tr.select_one('.td_headerandpost .subject > a').text
        body = tr.select_one('.td_headerandpost .post')
        message_number = tr.select_one('.td_headerandpost .message_number').text
        for tag in body.select('.quoteheader, .quote'):
            tag.decompose()
        body = body.text
        indexed_at = datetime.now().isoformat()
        _id = url[url.index('#msg') + 4:]
        document = {
            'authors': [author],
            'body': body,
            'body_type': 'raw',
            'domain': 'https://bitcointalk.org/',
            'url': url,
            'title': title,
            'id': f'bitcointalk-{_id}',
            'created_at': date,
            'indexed_at': indexed_at,
            'type': 'topic' if message_number == "#1" else "post"
        }
        documents.append(document)
    logger.info(f"Filtered {len(documents)} posts in {url}")
    return {'documents': documents, 'urls': urls}


def fetch_posts(url: str):
    resp = get_documents_from_post(url)
    documents = resp['documents']
    urls = resp['urls']
    for url in urls:
        logger.info(f"Downloading {url}...")
        resp = get_documents_from_post(url)
        documents.extend(resp['documents'])
        time.sleep(1)
    return documents


def main() -> None:
    filename = os.path.join(os.getenv('DATA_DIR'), 'bitcointalk', 'topics.json')
    topics = []
    if not os.path.exists(filename):
        topics = fetch_all_topics()
        with open(filename, 'w') as f:
            json.dump(topics, f)
    else:
        with open(filename, 'r') as f:
            topics = json.load(f)
    logger.info(f"Found {len(topics)} topics")
    count = 0
    start_index = int(os.getenv('START_INDEX')) if os.getenv('START_INDEX') else 0
    for i in range(start_index, len(topics)):
        topic = topics[i]
        logger.info(f"Processing {i + 1}/{len(topics)}")
        documents = fetch_posts(topic)
        for document in documents:
            res = upsert_document(index_name=os.getenv('INDEX'), doc_id=document['id'], doc_body=document)
            logger.info("Version-{}, Result-{}, ID-{}".format(res['_version'], res['result'], res['_id']))
            count += 1
    logger.info(f"Inserted {count} new documents")


if __name__ == "__main__":
    main()
