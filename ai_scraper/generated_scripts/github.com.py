import requests
from bs4 import BeautifulSoup
import json

def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string if soup.title else "NA"
    author = soup.find('span', class_='author').text.strip() if soup.find('span', class_='author') else "NA"
    created_at = soup.find('meta', {'name': 'created_at'})['content'] if soup.find('meta', {'name': 'created_at'}) else "NA"
    published_date = soup.find('meta', {'name': 'date'})['content'] if soup.find('meta', {'name': 'date'}) else "NA"
    
    topics = []
    for topic in soup.find_all('span', class_='Label'):
        topics.append(topic.text.strip())

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "created_at": created_at,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

main(url=globals().get('url'), filename=globals().get('filename'))