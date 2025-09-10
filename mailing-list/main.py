import os
import re
import sys
import traceback
import urllib.request
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dateutil import tz
from dotenv import load_dotenv
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.elasticsearch_utils import document_view, document_add

load_dotenv()

from config.conf import DATA_DIR, INDEX_NAME

DOWNLOAD_PATH = os.path.join(DATA_DIR, "mailing-list/bitcoin-dev")

ORIGINAL_URL = "https://gnusha.org/pi/bitcoindev/"
CUSTOM_URL = "https://mailing-list.bitcoindevs.xyz/bitcoindev/"

month_dict = {
    1: "Jan", 2: "Feb", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "Aug", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Dec"
}


def save_web_page(link, file_name):
    main_url = ORIGINAL_URL + link
    html_response = requests.get(f"{ORIGINAL_URL}{link}")

    soup = BeautifulSoup(html_response.content, 'html.parser')
    main_url_anchor = soup.new_tag("a", href=main_url.replace('#t', ''), id='main_url')
    soup.body.append(main_url_anchor)

    path = os.path.join(DOWNLOAD_PATH, file_name)
    with open(path, 'w', encoding='utf-8') as file:
        logger.info(f'Downloading {file_name}')
        file.write(str(soup))


def download_dumps(path, page_visited_count, max_page_count=2):
    if page_visited_count > max_page_count: return
    page_visited_count += 1
    logger.info(f"Page {page_visited_count}: {path}")
    with urllib.request.urlopen(f"{path}") as f:
        soup = BeautifulSoup(f, "html.parser")
        pre_tags = soup.find_all('pre')
        if len(pre_tags) < 1:
            return

        next_page_link = f"{ORIGINAL_URL}{soup.find('a', {'rel': 'next'}).get('href')}"
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


def extract_thread_structure(soup):
    """Extract threading information from the thread overview section"""
    thread_structure = []
    
    # Find the thread overview section
    pre_tags = soup.find_all('pre')
    for pre_tag in pre_tags:
        if "Thread overview:" in pre_tag.text:
            lines = pre_tag.get_text().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                    
                # Skip header lines
                if ("Thread overview:" in line or 
                    "expand[" in line or 
                    "mbox.gz" in line or
                    "Atom feed" in line or
                    "top" in line):
                    continue
                
                # Extract indentation level and content
                if (' `' in line or line.startswith('2')):  # Lines with dates/messages
                    # Count leading spaces and ` characters to determine depth
                    indent_level = 0
                    original_line = line
                    
                    # Calculate depth based on spaces before the backtick
                    # The pattern: more spaces before ` = deeper nesting
                    if '`' in line:
                        # Find position of backtick after the time
                        backtick_pos = line.find('`')
                        # Count spaces between time and backtick
                        time_end = re.search(r'\d{2}:\d{2}', line)
                        if time_end:
                            time_end_pos = time_end.end()
                            spaces_before_backtick = backtick_pos - time_end_pos - 1  # -1 for the space after time
                            # Each 2 additional spaces = one more level
                            indent_level = 1 + max(0, spaces_before_backtick // 2)
                        else:
                            indent_level = 1
                    else:
                        # No backtick = root message
                        indent_level = 0
                    
                    stripped = line.lstrip(' `')
                    
                    # Extract URL from href if present
                    href_match = re.search(r'href="([^"]+)"', line)
                    url = ""
                    if href_match:
                        url = href_match.group(1).replace('../', '')
                    
                    # Extract date (first part of line)
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', stripped)
                    if date_match:
                        date_str = date_match.group(1)
                        
                        # Extract message ID from URL or line
                        message_id = ""
                        if '#' in url:
                            message_id = url.split('#')[-1]
                        elif href_match:
                            # Try to extract message ID from href
                            href_url = href_match.group(1)
                            if '/' in href_url:
                                message_id = href_url.split('/')[-1].replace('.html', '')
                        
                        thread_structure.append({
                            'url': url,
                            'date': date_str,
                            'indent_level': indent_level,
                            'message_id': message_id,
                            'raw_line': original_line.strip()
                        })
    
    return thread_structure


def get_thread_urls_with_date(pre_tags):
    urls_dates = []
    date_time_pattern = r'\b\d{4}-\d{2}-\d{2} {1,2}(?:[01]?\d|2[0-3]):[0-5]\d\b'

    for pre_tag in reversed(pre_tags):
        if "links below jump to the message on this page" in pre_tag.text:
            anchor_tags = pre_tag.find_all('a', href=lambda href: href and '#' in href)

            for anchor in anchor_tags:
                date_search = re.search(date_time_pattern, anchor.previous_sibling.text)
                if date_search:
                    date = date_search.group()
                    original_datetime = datetime.strptime(date, '%Y-%m-%d %H:%M')
                    original_datetime = original_datetime.replace(tzinfo=tz.tzutc())
                    dt = original_datetime.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                    urls_dates.append((anchor, dt))

    # sort the urls_dates list by datetime in ascending order (earliest first)
    urls_dates.sort(key=lambda x: x[1])
    return urls_dates


def get_year_month(date):
    date = date.strip().split('-')
    year = int(date[0])
    month = int(date[1])
    return year, month


def get_author(text):
    from_user = re.search(r'From:\s*(.+?)\s+\@', text).group()
    # to_user = re.search(r'To:\s*(.+)', text).group()
    author = from_user.replace("From: ", "").replace("@", "").replace("'", "").replace(
        "via Bitcoin Development Mailing List", '').strip()
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
            with open(f'{os.path.join(root, file)}', 'r', encoding='utf-8') as f:
                u = file[9:].replace(".html", "")
                html_content = f.read()
                soup = BeautifulSoup(html_content, 'html.parser')

                # Extract thread structure
                thread_structure = extract_thread_structure(soup)

                # scrape url
                main_url = soup.find('a', id='main_url')
                main_url = main_url.get('href')

                # Scrape title
                title = soup.find_all('b')[1].text
                title = title.replace("[Bitcoin-development] ", "").replace("[bitcoin-dev] ", "").replace(
                    "[bitcoindev] ", "").replace("\t", "").strip()

                urls_with_date = get_thread_urls_with_date(soup.find_all('pre'))
                for index, (url, date) in enumerate(urls_with_date):
                    try:
                        year, month = get_year_month(date)
                        if year < 2024 or (year == 2024 and month == 1):
                            continue

                        href = url.get('href')
                        tag_id = url.get('id')
                        content = soup.find(lambda tag: tag.name == "pre" and tag.find('a', href=f"#{tag_id}"))

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

                        # Find threading info for this URL
                        thread_info = None
                        url_fragment = href.replace("#", "")
                        
                        for thread_item in thread_structure:
                            if url_fragment in thread_item.get('message_id', '') or url_fragment in thread_item.get('url', ''):
                                thread_info = thread_item
                                break

                        doc_id = f"mailing-list-{year}-{month:02d}-{href.replace('#', '')}"
                        document = {
                            "id": doc_id,
                            "authors": [author],
                            "title": title,
                            "body": body_text,
                            "body_type": "raw",
                            "created_at": date,
                            "domain": CUSTOM_URL,
                            "thread_url": main_url,
                            "url": f"{main_url}{href}",
                            # ADD THREAD INFO:
                            "thread_depth": thread_info['indent_level'] if thread_info else 0,
                            "thread_parent": None,  # We'll calculate this in the frontend
                            "message_id": href.replace('#', ''),
                        }

                        if index == 0:
                            document['type'] = "original_post"
                        else:
                            document['type'] = "reply"
                        doc.append(document)
                    except Exception as e:
                        logger.info(f"{e} \nORIGINAL_URL: {main_url}\n{traceback.format_exc()}")
                        continue
    return doc


def index_documents(docs):
    for doc in docs:

        resp = document_view(index_name=INDEX_NAME, doc_id=doc['id'])
        if not resp:
            _ = document_add(index_name=INDEX_NAME, doc=doc, doc_id=doc['id'])
            logger.success(f'Successfully added! ID: {doc["id"]}')
        else:
            logger.info(f"Document already exist! ID: {doc['id']}")


if __name__ == "__main__":
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    download_dumps(ORIGINAL_URL, page_visited_count=0)
    documents = parse_dumps()
    index_documents(documents)
