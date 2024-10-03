import sys
import traceback
from io import StringIO
from html.parser import HTMLParser
from elasticsearch import NotFoundError
import requests
import os
import subprocess
import platform
from loguru import logger
from tqdm import tqdm
import xml.etree.ElementTree as ET

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conf import ES

def document_add(index_name, doc, doc_id=None):
    resp = ES.index(index=index_name, body=doc, id=doc_id)
    return resp


def document_view(index_name, doc_id):
    try:
        resp = ES.get(index=index_name, id=doc_id)
    except NotFoundError:
        resp = False
    return resp


def find_and_delete_document_by_source_id(index_name, source_id):
    body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "term": {
                            "id.keyword": source_id
                        }
                    }
                ]
            }
        }
    }

    try:
        search_resp = ES.search(index=index_name, body=body, _source=False)
        hits = search_resp.get('hits', {}).get('hits', [])
        if not hits:
            logger.info(f"No documents found with source-id: {source_id}")
            return None

        document_to_delete_id = hits[0]['_id']
        logger.info(f"Document _id to delete: {document_to_delete_id}")

        delete_resp = ES.delete(index=index_name, id=document_to_delete_id)
        result = delete_resp.get('result', None)
        if result == 'deleted':
            logger.info(f"Deleted! '_id': '{document_to_delete_id}'")
            return document_to_delete_id
        else:
            logger.info("Failed to delete the document.")
            return None

    except Exception as e:
        logger.info(f"An error occurred: {e} \n{traceback.format_exc()}")
        return None


def parse_users(users_file_path) -> dict:
    users = {}
    tree = ET.parse(users_file_path)
    root = tree.getroot()
    for user in root:
        users[user.attrib.get("Id")] = user.attrib.get("DisplayName")
    logger.info(f"Number of users found: {len(users.keys())}")
    return users


def parse_posts(posts_file_path):
    tree = ET.parse(posts_file_path)
    root = tree.getroot()
    return root


def extract_dump(download_path, extract_path):
    try:
        logger.info('extracting the data...')
        if platform.system() == 'Windows':
            full_7z_path = r"C:\\Program Files\\7-Zip\\7z.exe"  # assuming the default path of 7z in Windows machine
            subprocess.check_call([full_7z_path, "x", "-o" + extract_path, download_path])
        else:
            print("Extracted Path", extract_path)
            subprocess.check_call(["7z", "x", "-o" + extract_path, download_path])
        logger.info(f"Extraction successful to path: {os.path.abspath(download_path)}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Extraction failed: {e}")


def download_dump(download_path):
    os.makedirs(os.path.dirname(download_path), exist_ok=True)
    logger.info('downloading the data from archive...')
    archive_url = "https://archive.org/download/stackexchange/bitcoin.stackexchange.com.7z"
    try:
        r = requests.get(archive_url, stream=True)
        if r.status_code == 200:
            with open(download_path, "wb") as f:
                for chunk in tqdm(r.iter_content(chunk_size=1024)):
                    if chunk:
                        f.write(chunk)
            logger.info(f"successfully downloaded data to path: {download_path}")
        else:
            logger.error(f"Request returned an error: {r.status_code}")
    except requests.RequestException as e:
        logger.error(f"An error occurred while downloading: {e}")


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()
