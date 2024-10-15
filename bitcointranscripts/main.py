import asyncio
import os
import re
import sys
import traceback
import zipfile
from datetime import datetime

import requests
import yaml
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.elasticsearch_utils import upsert_document
from common.utils import parse_markdown
from config.conf import DATA_DIR, INDEX_NAME

FOLDER_NAME = "bitcointranscripts-master"
REPO_URL = "https://github.com/bitcointranscripts/bitcointranscripts/archive/refs/heads/master.zip"

# Paths
DIR_PATH = os.path.join(DATA_DIR, "bitcointranscripts")
GLOBAL_URL_VARIABLE = os.path.join(DIR_PATH, FOLDER_NAME)


def download_repo():
    os.makedirs(DIR_PATH, exist_ok=True)

    if os.path.exists(GLOBAL_URL_VARIABLE):
        logger.info(f"Repo already downloaded at path: {DIR_PATH}")
        return

    logger.info(f"Downloading repo at path: {DIR_PATH}")
    file_path = os.path.join(DIR_PATH, "master.zip")

    try:
        response = requests.get(REPO_URL)
        response.raise_for_status()

        with open(file_path, 'wb') as file:
            file.write(response.content)
        logger.info(f"Downloaded {REPO_URL} to {file_path}")

        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(DIR_PATH)
        logger.info(f"Unzipped {file_path} to {DIR_PATH}")

    except requests.RequestException as e:
        logger.error(f"Failed to download the repo: {e}")

    except zipfile.BadZipFile as e:
        logger.error(f"Failed to unzip the file: {e}")


def parse_posts(directory):
    documents = []
    root_depth = directory.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(directory):
        current_depth = root.rstrip(os.sep).count(os.sep)
        if current_depth <= root_depth:
            continue
        for file in files:
            translated_transcript_pattern = r'\.([a-z][a-z])\.md$'
            transcript = file.endswith('.md')
            translated_transcript = re.search(translated_transcript_pattern, file)
            index_file = file.startswith('_')
            if transcript and not index_file and not translated_transcript:
                file_path = os.path.join(root, file)
                document = parse_post(file_path)
                documents.append(document)
    return documents


def parse_post(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    front_matter, body = parse_markdown(content)
    # Extract metadata from front matter using yaml
    metadata = yaml.safe_load(front_matter)
    url_path = os.path.normpath(file_path.replace('.md', '').replace(GLOBAL_URL_VARIABLE, ''))
    transcript_by = metadata.get('transcript_by', "")

    document = {
        'id': "bitcointranscripts" + url_path.replace(os.sep, "+"),
        'title': metadata['title'],
        'body_formatted': body,
        'body': body,
        'body_type': "markdown",
        'created_at': (datetime.strptime(metadata['date'], '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.000Z') if isinstance(metadata.get('date'), str) else None),
        'domain': "https://btctranscripts.com/",
        'url': "https://btctranscripts.com" + url_path.replace(os.sep, "/"),
        'categories': metadata.get('categories', []),
        'tags': metadata.get('tags', []),
        'media': metadata.get('media', ""),
        'authors': metadata.get('speakers', []),
        'indexed_at': datetime.now().isoformat(),
        'transcript_by': transcript_by,
        'needs_review': "--needs-review" in transcript_by,
        'transcript_source': url_path.split(os.sep)[1]
    }
    return document


async def main():
    download_repo()
    documents = parse_posts(GLOBAL_URL_VARIABLE)
    logger.info(f"Filtering existing {len(documents)} documents... please wait...")

    new_ids = set()
    updated_ids = set()
    for document in documents:
        try:
            # Update the provided fields with those in the existing document,
            # ensuring that any fields not specified in 'doc_body' remain unchanged in the ES document
            res = upsert_document(index_name=INDEX_NAME, doc_id=document['id'], doc_body=document)
            if res['result'] == 'created':
                logger.success(f"Version: {res['_version']}, Result: {res['result']}, ID: {res['_id']}")
                new_ids.add(res['_id'])
            if res['result'] == 'updated':
                updated_ids.add(res['_id'])
                logger.info(f"Version: {res['_version']}, Result: {res['result']}, ID: {res['_id']}")
        except Exception as ex:
            logger.error(f"{ex} \n{traceback.format_exc()}")
            logger.warning(document)

    logger.info(f"Inserted {len(new_ids)} new documents")
    logger.info(f"Updated {len(updated_ids)} documents")


if __name__ == '__main__':
    asyncio.run(main())
