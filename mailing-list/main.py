import os
import re
import traceback
import urllib.request
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dateutil import tz
from dotenv import load_dotenv
from loguru import logger
from elastic_utils import document_view, document_add

load_dotenv()

INDEX = os.getenv("INDEX")
BASE_DIR = os.getenv("DATA_DIR", ".")
DOWNLOAD_PATH = os.path.join(BASE_DIR, "mailing-list/bitcoin-dev")

URL = "https://gnusha.org/pi/bitcoindev/"

month_dict = {
    1: "Jan", 2: "Feb", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "Aug", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Dec"
}


def save_web_page(link, file_name):
    html = requests.get(f"{URL}{link}")
    path = os.path.join(DOWNLOAD_PATH, file_name)
    with open(path, 'w', encoding='utf-8') as file:
        logger.info(f'Downloading {file_name}')
        file.write(html.text)


def download_dumps(path, page_visited_count, max_page_count=2):
    if page_visited_count > max_page_count: return
    page_visited_count += 1
    logger.info(f"Page {page_visited_count}: {path}")
    with urllib.request.urlopen(f"{path}") as f:
        soup = BeautifulSoup(f, "html.parser")
        pre_tags = soup.find_all('pre')
        if len(pre_tags) < 1:
            return

        next_page_link = f"{URL}{soup.find('a', {'rel': 'next'}).get('href')}"

        for tag in pre_tags[1].find_all('a'):

            try:
                date = tag.next_sibling.strip()[:7]
                date = date.strip().split('-')

                # date = tag.next_sibling.strip()[:8]
                if len(date) < 2:
                    continue
                year = int(date[0])
                mon = int(date[1])
                month = month_dict.get(int(date[1]))
                if year < 2024 or (year == 2024 and mon == 1):
                    return

                href = tag.get('href')
                file_name = f"{year}-{month}-{href.strip().split('/')[0]}.html"

                save_web_page(href, file_name)

            except Exception as e:
                logger.error(e)
                logger.error(tag)
                continue
        logger.info('----------------------------------------------------------\n')
        if next_page_link:
            download_dumps(next_page_link, page_visited_count)


def get_thread_urls_with_date(pre_tags):
    for pre_tag in reversed(pre_tags):
        if "links below jump to the message on this page" in pre_tag.text:
            date_time_pattern = r'\b\d{4}-\d{2}-\d{2} {1,2}(?:[01]?\d|2[0-3]):[0-5]\d\b'

            anchor_tags = pre_tag.find_all('a', href=lambda href: href and '#' in href)
            urls_date = []
            for anchor in anchor_tags:
                date = re.search(date_time_pattern, anchor.previous_sibling.text).group()
                original_datetime = datetime.strptime(date, '%Y-%m-%d %H:%M')
                original_datetime = original_datetime.replace(tzinfo=tz.tzutc())
                dt = original_datetime.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                urls_date.append((anchor, dt))
            return urls_date


def get_year_month(date):
    date = date.strip().split('-')
    year = int(date[0])
    month = int(date[1])
    return year, month


def get_author(text):
    from_user = re.search(r'From:\s*(.+?)\s+\@', text).group()
    # to_user = re.search(r'To:\s*(.+)', text).group()
    author = from_user.replace("From: ", "").replace("@", "").strip()
    return author


def href_contains_text(tag, search_text):
    return tag.name == 'a' and tag.has_attr('href') and search_text in tag['href']


def preprocess_body_text(text):
    text = text.replace("[|]", "").strip()
    text = re.sub(r'\[not found\] <[^>]+>', "", text)
    text = re.sub(re.compile(
        r'You received this message because you are subscribed to the Google Groups .+? group.\s+'
        r'To unsubscribe from this group and stop receiving emails from it, send an email to .+?\.\s+'
        r'To view this discussion on the web visit .+\.',
        re.DOTALL
    ), '', text)
    return text


def parse_dumps():
    doc = []
    for root, dirs, files in os.walk(DOWNLOAD_PATH):
        for file in reversed(files):
            logger.info(f'parsing : {file}')
            with open(f'{os.path.join(root, file)}', 'r',
                      encoding='utf-8') as f:
                u = file[9:].replace(".html", "")
                main_url = f"{URL}{u}"
                html_content = f.read()
                soup = BeautifulSoup(html_content, 'html.parser')

                # Scrape title
                title = soup.find_all('b')[1].text
                title = title.replace("[Bitcoin-development] ", "").replace("[bitcoin-dev] ", "").replace(
                    "[bitcoindev] ", "").replace("\t", "").strip()

                urls_with_date = get_thread_urls_with_date(soup.find_all('pre'))

                for url, date in urls_with_date:
                    try:
                        year, month = get_year_month(date)

                        if year < 2024 or (year == 2024 and month == 1):
                            continue

                        href = url.get('href')

                        content = soup.find(lambda tag: tag.name == "pre" and tag.find('a', href=href))

                        # Scrape Body
                        for c in content.find_all('b'):
                            c.decompose()

                        for c in content.find_all('u'):
                            c.decompose()

                        for c in content.find_all(lambda tag: href_contains_text(tag, href.replace("#", "")[1:])):
                            c.decompose()

                        for c in content.find_all(lambda tag: href_contains_text(tag, u)):
                            c.decompose()

                        # for c in content.find_all(lambda tag: tag.name in {'b', 'u'} or any(
                        #         href_contains_text(tag, text) for text in [href.replace("#", "")[1:],u])):
                        #     c.decompose()
                        body_text = preprocess_body_text(content.text)

                        # Scraping author
                        author = get_author(body_text)

                        doc_id = f"mailing-list-{year}-{month_dict.get(int(month))}-{href.replace('#', '')}"
                        document = {
                            "id": doc_id,
                            "author": [author],
                            "title": title,
                            "body": body_text,
                            "body_type": "raw",
                            "created_at": date,
                            "domain": URL,
                            "url": f"{main_url}/{href}"
                        }
                        doc.append(document)
                    except Exception as e:
                        logger.warning(main_url + "/" + href)
                        logger.error(traceback.format_exc())
                        continue
    return doc


def index_documents(docs):
    for doc in docs:

        resp = document_view(index_name=INDEX, doc_id=doc['id'])
        if not resp:
            _ = document_add(index_name=INDEX, doc=doc, doc_id=doc['id'])
            logger.success(f'Successfully added! ID: {doc["id"]}')
        else:
            logger.info(f"Document already exist! ID: {doc['id']}")


if __name__ == "__main__":
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    download_dumps(URL, page_visited_count=0)
    documents = parse_dumps()
    index_documents(documents)
