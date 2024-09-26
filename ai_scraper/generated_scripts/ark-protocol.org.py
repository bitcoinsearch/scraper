import requests
from bs4 import BeautifulSoup
import json

def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string if soup.title else "NA"
    author = soup.find('meta', attrs={'name': 'author'})
    author = author['content'] if author else "NA"
    published_date = "NA"  # No specific date found in the provided content
    created_at = "NA"  # No specific created_at found in the provided content
    topics = []

    for section in soup.find_all(['h2', 'h4']):
        topics.append(section.get_text(strip=True))

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "created_at": created_at,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

# Driver code
url = url
filename = filename
main(url=url, filename=filename)