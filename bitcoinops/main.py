import argparse
import re
from datetime import datetime
from os import walk, getenv, makedirs
from os.path import join, exists, basename

import dotenv
import requests
import yaml
import zipfile
from loguru import logger

from common.elasticsearch_utils import upsert_document


def download_zip(source_url: str, download_dir, file_name="raw_data.zip", extract=True):
    try:
        if not exists(join(download_dir, file_name)):
            makedirs(download_dir, exist_ok=True)
            logger.info("Downloading Repo from {}.".format(source_url))
            response = requests.get(source_url)
            with open(join(download_dir, file_name), "wb") as zip_file:
                zip_file.write(response.content)
            print("Download Complete, repo stored at {}".format(join(download_dir, file_name)))
            if extract:
                logger.info("Extracting repo at {}.".format(join(download_dir, file_name[:-4:])))
                zip_file = zipfile.ZipFile(join(download_dir, file_name))
                zip_file.extractall(join(download_dir, file_name[:-4:]))
        else:
            logger.warning("Repo already downloaded")
        return True
    except Exception as e:
        logger.error(e)
        return False


def dir_walk(extracted_dir: str, typeof: str):
    if exists(extracted_dir):
        documents = []
        for file in walk(extracted_dir):
            dirs = file[1]
            files = file[2]
            for dir in dirs:
                documents.extend(dir_walk(join(file[0], dir), typeof))
                continue
            for post_file in files:
                logger.info("Parsing {}".format(join(file[0], post_file)))
                documents.append(parse_post(join(file[0], post_file), typeof))
            return documents

    else:
        logger.critical("Data Directory not available.")


def parse_post(post_file: str, typeof: str):
    try:
        with open(post_file, 'r', encoding='utf-8') as file:
            content = file.read()
        content = re.sub(r'{%.*%}', '', content, flags=re.MULTILINE)
        front_matter, body = parse_markdowns(content)
        metadata = yaml.safe_load(front_matter)
        custom_id = basename(post_file).replace('.md', '') if typeof == 'topic' else metadata['slug']
        document = {
            "id": "bitcoinops-" + custom_id,
            "title": metadata['title'],
            "body_formatted": body,
            "body": body,
            "body_type": "markdown",
            "created_at": metadata['date'].strftime('%Y-%m-%dT%H:%M:%S.000Z') if metadata.get('date') else None,
            "domain": "https://bitcoinops.org/en/",
            "url": "https://bitcoinops.org/en/topics/{}".format(
                custom_id + '.md') if typeof == "topic" else "https://bitcoinops.org${}".format(metadata['permalink']),
            "type": "topic" if typeof == "topic" else metadata['type'],
            "language": metadata['lang'] if 'lang' in metadata.keys() else 'en',
            "authors": ["bitcoinops"],
            "indexed_at": datetime.now().isoformat()
        }
        return document
    except IOError as e:
        logger.warning("Issue while parsing the file, {}".format(post_file))


def parse_markdowns(content: str):
    lines = content.split("\n")
    front_matter = False
    body_flag = False
    front_matter_list = []
    body_list = []

    for line in lines:
        if line.startswith("---"):
            if front_matter:
                front_matter = False
                body_flag = True
                continue
            if body_flag:
                break
            front_matter = True
            continue
        if front_matter:
            front_matter_list.append(line)
        elif body_flag:
            body_list.append(line)
    return '\n'.join(front_matter_list), '\n'.join(body_list)


def parseTopics():
    pass


def main(data_source_url: str, download_dir: str, file_name: str, postdir_path: str, topicdir_path: str) -> None:
    if download_zip(data_source_url, download_dir, file_name):
        all_post = dir_walk(join(download_dir, file_name[:-4:], postdir_path), "posts")
        all_topic = dir_walk(join(download_dir, file_name[:-4:], topicdir_path), "topic")
        all_post.extend(all_topic)
        cnt = 0
        for post in all_post:
            try:
                res = upsert_document(index_name=getenv('INDEX'), doc_id=post['id'], doc_body=post)
                cnt += 1
                logger.info("Version-{}, Result-{}, ID-{}".format(res['_version'], res['result'], res['_id']))
            except Exception as e:
                logger.error("Error: {}".format(e))
                logger.warning(post)
        logger.info("Total Post Inserted/Updated-{}".format(cnt))
    else:
        raise Exception


if __name__ == "__main__":
    dotenv.load_dotenv()
    parser = argparse.ArgumentParser(description="Bitcoin Optech scraper")
    parser.add_argument("-U", "--sourceUrl",
                        default="https://github.com/bitcoinops/bitcoinops.github.io/archive/refs/heads/master.zip")
    parser.add_argument("-D", "--downloadDir", default=getenv("DATA_DIR"))
    parser.add_argument("-F", "--fileName", default="raw_data.zip")
    parser.add_argument("-P", "--postDir", default="bitcoinops.github.io-master/_posts/en")
    parser.add_argument("-T", "--topicDir", default="bitcoinops.github.io-master/_topics/en")
    args = parser.parse_args()
    url = args.sourceUrl
    download_dir = args.downloadDir
    output_file_name = args.fileName
    post_dir = args.postDir
    topic_dir = args.topicDir
    main(url, download_dir, output_file_name, post_dir, topic_dir)
