import asyncio
import os
import re
import zipfile
from datetime import datetime
import traceback

import requests
import yaml
from dotenv import load_dotenv
from loguru import logger

from common.elasticsearch_utils import upsert_document

load_dotenv()

folder_name = "bitcointranscripts-master"
index_name = os.getenv('INDEX')


def download_repo():
    URL = "https://github.com/bitcointranscripts/bitcointranscripts/archive/refs/heads/master.zip"
    data_dir = os.getenv('DATA_DIR')
    dir_path = os.path.join(data_dir, "bitcointranscripts")
    os.makedirs(dir_path, exist_ok=True)

    if os.path.exists(os.path.join(dir_path, folder_name)):
        logger.info(f"Repo already downloaded at path: {dir_path}")
        return

    logger.info(f"Downloading repo at path: {dir_path}")
    file_path = os.path.join(dir_path, "master.zip")

    # Download the file
    response = requests.get(URL)
    with open(file_path, 'wb') as file:
        file.write(response.content)

    logger.info(f"Downloaded {URL} to {file_path}")

    # Unzip
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(dir_path)

    logger.info(f"Unzipped {file_path} to {dir_path}")


def parse_posts(directory):
    documents = []
    root_depth = directory.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(directory):
        current_depth = root.rstrip(os.sep).count(os.sep)
        if current_depth <= root_depth:
            continue
        for file in files:
            if file.endswith('.md') and not file.startswith('_') and not re.search(r'\.([a-z][a-z])\.md$', file):
                file_path = os.path.join(root, file)
                document = parse_post(file_path)
                documents.append(document)
    return documents


def parse_post(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Remove content between {% %}
    content = re.sub(r'{%.*%}', '', content, flags=re.MULTILINE)
    front_matter, body = parse_markdown(content)

    # Extract metadata from front matter using yaml
    metadata = yaml.safe_load(front_matter)

    custom_id = file_path.replace('.md', '').replace(os.path.join(os.getenv('DATA_DIR'), "bitcointranscripts", folder_name), '')

    document = {
        'id': "bitcointranscripts" + custom_id.replace("\\", "+").replace("/", "+"),
        'title': metadata['title'],
        'body_formatted': body,
        'body': body,
        'body_type': "text",
        'created_at': metadata['date'].strftime('%Y-%m-%dT%H:%M:%S.000Z') if metadata.get('date') else None,
        'domain': "https://btctranscripts.com/",
        'url': "https://btctranscripts.com" + custom_id.replace("\\", "/"),
        'categories': metadata.get('categories', []),
        'tags': metadata.get('tags', []),
        'media': metadata.get('media', ""),
        'authors': metadata.get('speakers', []),
        'indexed_at': datetime.now().isoformat(),
        'transcript_by': metadata.get('transcript_by', "")
    }
    return document


def parse_markdown(text):
    lines = text.split('\n')
    in_front_matter = False
    in_body = False
    front_matter = []
    body = []

    for line in lines:
        if line.startswith('---'):
            if in_front_matter:
                in_front_matter = False
                in_body = True
                continue
            if in_body:
                break
            in_front_matter = True
            continue

        if in_front_matter:
            front_matter.append(line)
        elif in_body:
            body.append(line)

    return '\n'.join(front_matter), '\n'.join(body)


async def main():
    download_repo()
    dir_path = os.path.join(os.getenv('DATA_DIR'), "bitcointranscripts", folder_name)
    documents = parse_posts(dir_path)
    logger.info(f"Filtering existing {len(documents)} documents... please wait...")

    count = 0
    for document in documents:
        try:
            # Update the provided fields with those in the existing document,
            # ensuring that any fields not specified in 'doc_body' remain unchanged in the ES document
            response = upsert_document(index_name=index_name, doc_id=document['id'], doc_body=document)
            count += 1
            logger.info(f"Version: {response['_version']}, Result: {response['result']}, ID: {response['_id']}, ")
        except Exception as ex:
            logger.error(f"{ex} \n{traceback.format_exc()}")
            logger.warning(document)

    logger.info(f"Inserted/Updated {count} documents")


if __name__ == '__main__':
    asyncio.run(main())
