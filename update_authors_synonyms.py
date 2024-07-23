import csv
import os
import re
import sys
import time
import traceback
from ast import literal_eval

import requests
from loguru import logger
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.elasticsearch_utils import extract_data_from_es, es

INDEX = os.getenv("INDEX")

# URL of the CSV file in the GitHub (bitcoinsearch/synonyms/authors-synonyms.csv)
URL = 'https://raw.githubusercontent.com/bitcoinsearch/synonyms/main/authors-synonyms.csv'


def get_author_synonyms_mapping(url):
    response = requests.get(url)
    response.raise_for_status()

    mapping = {}
    lines = response.text.splitlines()
    reader = csv.reader(lines)
    for row in reader:
        uniform_name = row[0]  # the first name is considered as the default name to be set
        for name in row:
            try:
                name = literal_eval(name.strip())
            except:
                name = name.strip()
            mapping[name] = uniform_name
    if mapping:
        logger.info(f"Authors synonyms fetched successfully!")
    return mapping


def remove_timestamps_from_author_names(author_list):
    timestamp_pattern = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\+\d{2}:\d{2})?')  # YYYY-MM-DD HH:MM:SS±HH:MM
    preprocessed_list = []

    for author in author_list:
        if timestamp_pattern.search(author):
            name = author.split(" ")[0:-2]
            name = ' '.join(name)
            if name.endswith(" ."):
                name = name.replace(" .", "")
            preprocessed_list.append(name.strip())
        else:
            preprocessed_list.append(author.strip())

    if not preprocessed_list or all(not name for name in preprocessed_list):
        logger.warning(f"{author_list} ---> {preprocessed_list}")
        time.sleep(5)

    return list(set(preprocessed_list))


if __name__ == "__main__":

    synonym_mapping = get_author_synonyms_mapping(URL)

    dev_urls = [
        "https://lists.linuxfoundation.org/pipermail/lightning-dev/",
        "https://lists.linuxfoundation.org/pipermail/bitcoin-dev/",
        "https://gnusha.org/pi/bitcoindev/",
        "https://mailing-list.bitcoindevs.xyz/bitcoindev/",
        "https://delvingbitcoin.org/",
        "https://bitcointalk.org/",
        "https://bitcoinops.org/en/",
        "https://bitcoin.stackexchange.com",
        "https://btctranscripts.com/"
    ]

    for domain_url in dev_urls:
        docs_list = extract_data_from_es(index=INDEX, domain=domain_url)
        if docs_list:
            logger.info(f"Number of documents received for {domain_url}: {len(docs_list)}")

            for doc in tqdm(docs_list):
                res = None
                try:
                    doc_id = doc['_id']
                    doc_index = doc['_index']
                    current_authors = doc['_source'].get('authors')

                    if current_authors:
                        current_authors = remove_timestamps_from_author_names(current_authors)
                    else:
                        logger.warning(f"'authors': {current_authors} || {doc_id}")
                        continue

                    if current_authors:
                        updated_authors = [synonym_mapping.get(a, a) for a in current_authors]
                        doc['_source']['authors'] = updated_authors

                        res = es.update(
                            index=doc_index,
                            id=doc_id,
                            doc=doc['_source'],
                            doc_as_upsert=True
                        )
                        logger.info(
                            f"{current_authors} ---> {updated_authors} || "
                            f"Version: {res['_version']}, Result: {res['result']}, ID: {res['_id']}"
                        )

                    else:
                        logger.warning(f"Unable to parse 'authors' for DOC ID: {doc_id}")

                except Exception as ex:
                    logger.error(f"Error occurred: {ex} \n{traceback.format_exc()}")

    logger.success(f"Process complete.")
