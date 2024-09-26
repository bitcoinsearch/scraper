import requests
from bs4 import BeautifulSoup
import json

def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string if soup.title else "NA"
    author = "NA"
    published_date = "NA"
    topics = []

    author_tag = soup.find('meta', attrs={'name': 'author'})
    if author_tag and 'content' in author_tag.attrs:
        author = author_tag['content']

    date_tag = soup.find('time')
    if date_tag and 'datetime' in date_tag.attrs:
        published_date = date_tag['datetime']

    topics_tags = soup.find_all('a', class_='topic-link')
    for tag in topics_tags:
        if tag.string:
            topics.append(tag.string.strip())

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

main(url=url, filename=filename)