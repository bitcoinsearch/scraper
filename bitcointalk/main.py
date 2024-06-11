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
            response = request('get', url)
            if response.status_code != 200:
                logger.error(f"Error {response.status_code} downloading page {offset // 40}")
                time.sleep(2)
                continue

            success = True
            soup = BeautifulSoup(response.text, 'html.parser')
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

    return topics


def get_documents_from_post(url: str) -> dict:
    response = request('get', url)
    if response.status_code >= 500 or response.status_code == 403:
        logger.error(f"Error {response.status_code} downloading {url}")
        time.sleep(10)
        return get_documents_from_post(url)

    soup = BeautifulSoup(response.text, 'html.parser')
    urls = list(set([a.get('href') for a in soup.find_all(class_='navPages')]))
    table = soup.select_one('#quickModForm > table:nth-child(1)')
    first_tr_class = table.find('tr').get('class')
    tr_list = table.find_all('tr', class_=first_tr_class)
    logger.info(f"Found {len(tr_list)} posts in {url}")

    documents = []
    for tr in tr_list:
        try:
            author = tr.select_one('.poster_info > b > a').text
        except:
            continue

        if author not in authors:
            continue

        logger.info(f"Post by: {author}")
        date_text = tr.select_one('.td_headerandpost .smalltext').text.strip()

        # Extract the actual date part from the string
        if 'Last edit:' in date_text:
            date_text = date_text.split('Last edit:')[-1].strip()

        date_parts = date_text.split('by')[0].strip()

        if 'Today at' in date_parts:
            date_parts = date_parts.replace('Today at', datetime.now().strftime('%B %d, %Y,'))

        date = datetime.strptime(date_parts, '%B %d, %Y, %I:%M:%S %p')
        post_url = tr.select_one('.td_headerandpost .subject > a').get('href')
        title = tr.select_one('.td_headerandpost .subject > a').text
        body = tr.select_one('.td_headerandpost .post')
        message_number = tr.select_one('.td_headerandpost .message_number').text

        for tag in body.select('.quoteheader, .quote'):
            tag.decompose()

        body = body.text.strip()
        indexed_at = datetime.now().isoformat()
        _id = post_url[post_url.index('#msg') + 4:]

        document = {
            'authors': [author],
            'body': body,
            'body_type': 'raw',
            'domain': 'https://bitcointalk.org/',
            'url': post_url,
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
    new_ids = set()
    updated_ids = set()
    start_index = int(os.getenv('START_INDEX', 0))
    for i in range(start_index, len(topics)):
        topic = topics[i]
        logger.info(f"Processing {i + 1}/{len(topics)}")
        documents = fetch_posts(topic)
        for document in documents:
            res = upsert_document(index_name=os.getenv('INDEX'), doc_id=document['id'], doc_body=document)
            logger.info("Version-{}, Result-{}, ID-{}".format(res['_version'], res['result'], res['_id']))
            if res['result'] == 'created':
                new_ids.add(res['_id'])
            if res['result'] == 'updated':
                updated_ids.add(res['_id'])
    logger.info(f"Inserted {len(new_ids)} new documents")
    logger.info(f"Updated {len(updated_ids)} documents")


if __name__ == "__main__":
    main()
