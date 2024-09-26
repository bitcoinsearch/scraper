import requests
from bs4 import BeautifulSoup
import json

def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('h1').get_text(strip=True) if soup.find('h1') else None
    author = soup.find('a', href="/author/jameson-lopp/").get_text(strip=True) if soup.find('a', href="/author/jameson-lopp/") else "NA"
    published_date = soup.find('time')['datetime'] if soup.find('time') else "NA"
    topics = [tag.get_text(strip=True) for tag in soup.find_all('a', class_='post-tag global-tag')]

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

main(url=globals().get('url'), filename=globals().get('filename'))