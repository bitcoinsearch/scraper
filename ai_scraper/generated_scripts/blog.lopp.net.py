import requests
from bs4 import BeautifulSoup
import json

def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('h1', class_='single-title').get_text(strip=True) if soup.find('h1', class_='single-title') else None
    author = soup.find('div', class_='author-name').get_text(strip=True) if soup.find('div', class_='author-name') else "NA"
    published_date = soup.find('time', class_='single-meta-date').get_text(strip=True) if soup.find('time', class_='single-meta-date') else "NA"
    topics = [tag.get_text(strip=True) for tag in soup.find_all('a', class_='post-tag')] if soup.find_all('a', class_='post-tag') else []

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "created_at": published_date,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

# Driver code
main(url=url, filename=filename)