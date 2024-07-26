import csv
import os
import sys
import traceback
from ast import literal_eval

import requests
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.elasticsearch_utils import update_authors_names_from_es

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
            if name != uniform_name:
                mapping[name] = uniform_name
    if mapping:
        logger.info(f"Authors synonyms fetched successfully!")
    return mapping


if __name__ == "__main__":
    synonym_mapping = get_author_synonyms_mapping(URL)

    for alias, default_name in synonym_mapping.items():
        try:
            res = update_authors_names_from_es(index=INDEX, old_author=alias.strip(), new_author=default_name)
        except Exception as ex:
            logger.error(f"Error occurred: {ex} \n{traceback.format_exc()}")

    logger.info("Author synonyms updated successfully.")
