import html
import json
import os
import sys
from datetime import datetime

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger as log

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.elasticsearch_utils import document_add, document_view, create_index

from achieve import download_dumps

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

# Get environment variables for path and index name
INDEX = os.getenv("INDEX")
ARCHIVE = os.getenv("ARCHIVE") or "archive"
SUB_ARCHIVE = os.getenv("SUB_ARCHIVE") or "posts"

# Create Index if it doesn't exist
if create_index(INDEX):
    log.info(f"Index: {INDEX}, created successfully.")
else:
    log.info(f"Index: {INDEX}, already exist.")

# Specify the path to the folder containing JSON files
folder_path = os.path.join(os.getcwd(), ARCHIVE, SUB_ARCHIVE)


def preprocess_body(text):
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    text = html.unescape(text)
    text = text.strip()
    return text


def strip_attributes(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all():
        tag.attrs = {}
    return str(soup)


def strip_attributes_but_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all():
        if tag.name not in ['a', 'img']:  # preserve a and img tags
            tag.attrs = {}
        else:  # for a and img tags, preserve href and src respectively
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in ['href', 'src']:
                    del tag.attrs[attr]
    return str(soup)


def index_documents(files_path):
    # Iterate through files in the specified path
    for root, dirs, files in os.walk(files_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                log.info(f'Fetching document from file: {file_path}')

                # Load JSON data from file
                with open(file_path, 'r', encoding='utf-8') as json_file:
                    document = json.load(json_file)

                body = preprocess_body(document['raw'])
                if body == "(post deleted by author)":
                    log.info(f"Probably, post deleted by an author: {body}")
                    continue

                # Select required fields
                doc = {
                    'id': f'delving-bitcoin-{document["topic_id"]}-{document["post_number"]}-{document["id"]}',
                    'authors': [document['username']],
                    'thread_url': f"https://delvingbitcoin.org/t/{document['topic_slug']}/{document['topic_id']}",
                    'title': document['topic_title'],
                    'body_type': 'html',
                    'body': body,
                    'body_formatted': strip_attributes_but_urls(document['cooked']),
                    'created_at': document['updated_at'],
                    'domain': "https://delvingbitcoin.org/",
                    'url': f"https://delvingbitcoin.org/t/{document['topic_slug']}/{document['topic_id']}",
                    "indexed_at": datetime.utcnow().isoformat()
                }

                if document['post_number'] != 1:
                    doc['url'] += f'/{document["post_number"]}'
                    doc['type'] = 'reply'
                else:
                    doc['type'] = 'original_post'

                # Check if a document already exists
                resp = document_view(index_name=INDEX, doc_id=doc['id'])
                if not resp:
                    _ = document_add(index_name=INDEX, doc=doc, doc_id=doc['id'])
                    log.success(f'Successfully added! ID: {doc["id"]}, Type:{doc["type"]}')
                else:
                    log.info(f"Document already exist! ID: {doc['id']}")


if __name__ == "__main__":
    download_dumps()
    log.info(f"Looking data in folder path: {folder_path}")
    index_documents(folder_path)
    log.info(f'{("-" * 20)}DONE{("-" * 20)}')
