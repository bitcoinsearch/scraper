import asyncio
import os
import re
import zipfile
from datetime import datetime

import requests
import yaml
from dotenv import load_dotenv
from loguru import logger

from common.elasticsearch_utils import upsert_document

load_dotenv()

FOLDER_NAME = "raw_data"
REPO_URL = "https://github.com/bitcoinops/bitcoinops.github.io/archive/refs/heads/master.zip"
POST_DIR = "bitcoinops.github.io-master/_posts/en"
TOPIC_DIR = "bitcoinops.github.io-master/_topics/en"

INDEX_NAME = os.getenv('INDEX')
DATA_DIR = os.getenv('DATA_DIR')

# Paths
DIR_PATH = os.path.join(DATA_DIR, "bitcoinops_dir")
GLOBAL_URL_VARIABLE = os.path.join(DIR_PATH, FOLDER_NAME)


async def download_repo():
    os.makedirs(DIR_PATH, exist_ok=True)

    if os.path.exists(GLOBAL_URL_VARIABLE):
        logger.info(f"Repo already downloaded at path: {DIR_PATH}")
        return

    logger.info(f"Downloading repo at path: {DIR_PATH}")
    file_path = os.path.join(DIR_PATH, "raw_data.zip")

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


def parse_markdowns(content: str):
    sections = re.split(r'---\n', content)
    if len(sections) < 3:
        raise ValueError("Input text does not contain proper front matter delimiters '---'")
    front_matter = sections[1].strip()
    body = sections[2].strip()
    return front_matter, body


def parse_post(post_file: str, typeof: str):
    try:
        with open(post_file, 'r', encoding='utf-8') as file:
            content = file.read()
        content = re.sub(r'{%.*%}', '', content, flags=re.MULTILINE)
        front_matter, body = parse_markdowns(content)
        metadata = yaml.safe_load(front_matter)
        custom_id = os.path.basename(post_file).replace('.md', '') if typeof == 'topic' else metadata['slug']
        document = {
            "id": f"bitcoinops-{custom_id}",
            "title": metadata['title'],
            "body_formatted": body,
            "body": body,
            "body_type": "markdown",
            "created_at": metadata.get('date').strftime('%Y-%m-%dT%H:%M:%S.000Z') if metadata.get('date') else None,
            "domain": "https://bitcoinops.org/en/",
            "url": f"https://bitcoinops.org/en/topics/{custom_id}" if typeof == "topic" else f"https://bitcoinops.org{metadata['permalink']}",
            "type": "topic" if typeof == "topic" else metadata['type'],
            "language": metadata.get('lang', 'en'),
            "authors": ["bitcoinops"],
            "indexed_at": datetime.now().isoformat()
        }
        return document
    except IOError as e:
        logger.warning(f"Issue while parsing the file, {post_file}: {e}")
        return None


def dir_walk(extracted_dir: str, typeof: str):
    if os.path.exists(extracted_dir):
        documents = []
        for root, dirs, files in os.walk(extracted_dir):
            for dir in dirs:
                documents.extend(dir_walk(os.path.join(root, dir), typeof))
            for post_file in files:
                logger.info(f"Parsing {os.path.join(root, post_file)}")
                document = parse_post(os.path.join(root, post_file), typeof)
                if document:
                    documents.append(document)
        return documents
    else:
        logger.critical("Data Directory not available.")
        return []


async def main():
    await download_repo()
    all_posts = dir_walk(os.path.join(DIR_PATH, POST_DIR), "posts")
    all_topics = dir_walk(os.path.join(DIR_PATH, TOPIC_DIR), "topic")
    new_ids = set()
    updated_ids = set()
    all_posts.extend(all_topics)
    for post in all_posts:
        try:
            res = upsert_document(index_name=INDEX_NAME, doc_id=post['id'], doc_body=post)
            logger.info(f"Version-{res['_version']}, Result-{res['result']}, ID-{res['_id']}")
            if res['result'] == 'created':
                new_ids.add(res['_id'])
            if res['result'] == 'updated':
                updated_ids.add(res['_id'])
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.warning(post)
    logger.info(f"Inserted {len(new_ids)} new documents")
    logger.info(f"Updated {len(updated_ids)} documents")


if __name__ == '__main__':
    asyncio.run(main())
