import os
import json
from dotenv import load_dotenv
import html
from bs4 import BeautifulSoup
from loguru import logger as log
from datetime import datetime

# from loguru import logger
from elastic import create_index, document_add, document_exist, document_view
from achieve import download_dumps

dotenv_path = os.path.join(os.path.dirname(__file__),'..','.env')
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

# # Get the directory where the Python script is located
# script_dir = os.path.dirname(os.path.realpath(__file__))

# Specify the path to the folder containing JSON files
folder_path = os.path.join(os.getcwd(), ARCHIVE, SUB_ARCHIVE)


def preprocess_body(text):
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    text = html.unescape(text)
    text = text.strip()
    return text


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

                # Select required fields
                doc = {
                    'id': f'{document["id"]}_{document["username"]}_{document["topic_slug"]}_{document["post_number"]}',
                    'authors': [document['username']],
                    'thread_url': f"https://delvingbitcoin.org/t/{document['topic_slug']}/{document['topic_id']}",
                    'title': document['topic_title'],
                    'body_type': 'raw',
                    'body': document['raw'],
                    'body_formatted': preprocess_body(document['raw']),
                    'created_at': document['updated_at'],
                    'domain': "https://delvingbitcoin.org/",
                    'url': f"https://delvingbitcoin.org/t/{document['topic_slug']}/{document['topic_id']}",
                    "indexed_at": datetime.utcnow().isoformat()
                }

                if document['post_number'] != 1:
                    doc['url'] += f'/{document["post_number"]}'
                    doc['type'] = 'reply'
                    doc['thread_url'] += f'/{document["post_number"]}'
                else:
                    doc['type'] = 'original'

                # Check if document already exist
                resp = document_view(index_name=INDEX, doc_id=doc['id'])
                if not resp:
                    resp = document_add(index_name=INDEX, doc=doc, doc_id=doc['id'])
                    log.success(f'Successfully added! ID: {doc["id"]}, Title: {doc["title"]}, Type:{doc["body_type"]}')
                else:
                    log.info(f"Document already exist! ID: {doc['id']}")


if __name__ == "__main__":
    no_new_posts = download_dumps()
    log.info(f"Looking data in folder path: {folder_path}")
    index_documents(folder_path)
    log.info(f'{("-" * 20)}DONE{("-" * 20)}')
