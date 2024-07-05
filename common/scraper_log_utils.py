import csv
import os
import sys
from datetime import datetime

from loguru import logger as log

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.elasticsearch_utils import get_domain_counts


def log_csv(scraper_domain, inserted=None, updated=None, no_changes=None, folder_path="scraper_logs", error="False",
            error_log="---"):
    date = datetime.utcnow().strftime("%d")
    month_year = datetime.utcnow().strftime("%Y_%m")
    time = datetime.utcnow().strftime("%H:%M:%S")

    log_folder_path = os.path.join(folder_path, month_year)
    if not os.path.exists(log_folder_path):
        os.makedirs(log_folder_path)

    csv_file_path = os.path.join(log_folder_path, f'{date}_logs.csv')
    with open(csv_file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        if csv_file.tell() == 0:
            writer.writerow(
                ['Date', 'Time', 'Scraper name', 'Inserted records', 'Updated records', 'No changes records',
                 'Total records', 'Error', 'Error log'])
        total_docs = get_domain_counts(index_name=os.getenv('INDEX'), domain=scraper_domain)
        writer.writerow([date, time, scraper_domain, inserted, updated, no_changes, total_docs, error, error_log])
    log.success("CSV Update Successfully :)")
