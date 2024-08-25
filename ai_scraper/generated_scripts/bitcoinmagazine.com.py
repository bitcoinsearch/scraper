import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string if soup.title else "NA"
    author = "NA"
    published_date = "NA"
    topics = []

    # Example extraction logic (this will depend on the actual HTML structure)
    author_tag = soup.find('meta', attrs={'name': 'author'})
    if author_tag and 'content' in author_tag.attrs:
        author = author_tag['content']

    date_tag = soup.find('time')
    if date_tag and 'datetime' in date_tag.attrs:
        published_date = date_tag['datetime']

    # Assuming topics are in a specific tag, e.g., <meta name="keywords">
    topics_tag = soup.find('meta', attrs={'name': 'keywords'})
    if topics_tag and 'content' in topics_tag.attrs:
        topics = topics_tag['content'].split(',')

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


main(url=url, filename=filename)
