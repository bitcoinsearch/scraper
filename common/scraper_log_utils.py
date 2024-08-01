import csv
import os
import sys
from datetime import datetime

from loguru import logger as log

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.elasticsearch_utils import get_domain_counts


def scraper_log_csv(csv_name, scraper_domain, inserted_docs, updated_docs, no_changes_docs, error=None):
    last_scraped = datetime.now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    total_docs = get_domain_counts(index_name=os.getenv('INDEX'), domain=scraper_domain)
    row = [last_scraped, scraper_domain, total_docs, inserted_docs, updated_docs, no_changes_docs, error]

    dir_path = "./scraper_logs/"

    os.makedirs(dir_path, exist_ok=True)
    with open(f"{dir_path}/{csv_name}", mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        if csv_file.tell() == 0:
            writer.writerow(
                ['last_scraped', 'source', 'total_docs', 'inserted_docs', 'updated_docs', 'no_changed_docs', 'error'])
        writer.writerow(row)
        log.success("CSV Update Successfully")

    log.info(f"Inserted Docs: {inserted_docs}")
    log.info(f"Updated Docs: {updated_docs}")
    log.info(f"No changed Docs: {no_changes_docs}")
    log.info(f"Error Message: {error}")
