import requests
from bs4 import BeautifulSoup
from typing import List
import os
import io
from PyPDF2 import PdfFileReader
import fitz
import json
from datetime import datetime
from urllib.parse import urljoin
from elastic_utils import document_view, document_add, document_exist
from loguru import logger

INDEX = os.getenv("INDEX")

def get_pdf_links(url: str) -> List[str]:
    """
    Get the links to pdf files from the given URL

    Args:
        url (str): The URL to scrape

    Returns:
        List[str]: The links to pdf files
    """
    html_content = requests.get(url).content
    soup = BeautifulSoup(html_content, 'html.parser')

    pdf_link_v2 = []
    for link in soup.select("a[href$='.pdf']"):
        pdf_link_v2.append(link['href'])

    return pdf_link_v2


def download_pdf(url, output_path):
    response = requests.get(url)
    with open(output_path, 'wb') as file:
        file.write(response.content)


def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text


def parse_text_to_metadata(text, pdf_url):
    lines = text.split('\n')
    title = lines[0] if lines else "No Title"
    authors = lines[1] if len(lines) > 1 else "Unknown"
    body = "\n".join(lines)
    metadata = {
        'id': f'id-{pdf_url.split("/")[-1].replace(".pdf", "")}',
        'title': title,
        'body': body,
        'authors': authors,
        'created_at': None,
        'indexed_at': datetime.utcnow().isoformat(),
        'url': pdf_url,
        'domain': "https://variable-website.com/",
        'body_type': "text"
    }
    return metadata


def index_documents(docs):
    # resp = document_view(index_name=INDEX, doc_id=docs['id'])
    resp = document_exist(index_name=INDEX, doc_id=docs['id'])
    if not resp:
        _ = document_add(index_name=INDEX, doc=docs, doc_id=docs['id'])
        logger.success(f'Successfully added! ID: {docs["id"]}')
    else:
        logger.info(f"Document already exist! ID: {docs['id']}")


url = "http://www.gatsby.ucl.ac.uk/teaching/courses/ml1-2016.html"
pdf_links = get_pdf_links(url)

base_url = "http://www.gatsby.ucl.ac.uk/teaching/courses/ml1-2016/"
output_dir = "output"

# Ensure output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

for pdf_link in pdf_links:
    pdf_url = urljoin(base_url, os.path.basename(pdf_link))
    pdf_path = os.path.join(output_dir, os.path.basename(pdf_link))

    try:
        download_pdf(pdf_url, pdf_path)
    except Exception as e:
        logger.error(f"Failed to download {pdf_url}: {e}")
        continue

    try:
        text = extract_text_from_pdf(pdf_path)
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        continue

    metadata = parse_text_to_metadata(text, pdf_url)

    output_json_path = os.path.join(output_dir, os.path.splitext(os.path.basename(pdf_link))[0] + ".json")
    try:
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(metadata, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to write metadata to {output_json_path}: {e}")
        continue

    try:
        with open(output_json_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        index_documents(data)
    except Exception as e:
        logger.error(f"Failed to index document from {output_json_path}: {e}")
        continue