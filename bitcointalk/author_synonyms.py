import csv
import os
import sys
import traceback
from ast import literal_eval

import requests
from loguru import logger
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.elasticsearch_utils import fetch_data_based_on_domain, es

INDEX = os.getenv("INDEX")

if __name__ == "__main__":
    # URL of the CSV file in the GitHub (bitcoinsearch/synonyms/authors-synonyms.csv)
    url = 'https://raw.githubusercontent.com/bitcoinsearch/synonyms/main/authors-synonyms.csv'

    response = requests.get(url)
    response.raise_for_status()

    # prepare the mapping for author synonyms
    synonym_mapping = {}
    lines = response.text.splitlines()
    reader = csv.reader(lines)
    for row in reader:
        uniform_name = row[0]  # the first name is considered as the default name to be set
        for name in row:
            try:
                name = literal_eval(name.strip())
            except:
                name = name.strip()

            synonym_mapping[name] = uniform_name

    # fetch the docs from ES index
    docs_list = fetch_data_based_on_domain(index=INDEX, domain="https://bitcointalk.org/")
    logger.info(f"Number of documents received: {len(docs_list)}")

    for doc in tqdm(docs_list):
        res = None
        try:
            doc_id = doc['_id']
            doc_index = doc['_index']
            current_authors = doc['_source'].get('authors')
            if current_authors:
                updated_authors = [synonym_mapping.get(a, a) for a in current_authors]
                doc['_source']['authors'] = updated_authors

                # update ES doc with latest author names
                res = es.update(
                    index=doc_index,
                    id=doc_id,
                    doc=doc['_source'],
                    doc_as_upsert=True
                )
                logger.info(f"{current_authors} changed to {updated_authors} || Version: {res['_version']}, Result: {res['result']}, ID: {res['_id']}")

        except Exception as ex:
            logger.error(f"Error occurred: {ex} \n{traceback.format_exc()}")

    logger.success(f"Process complete.")
