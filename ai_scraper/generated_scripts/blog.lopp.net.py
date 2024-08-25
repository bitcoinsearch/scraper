import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('h1', class_='single-title').get_text(strip=True) if soup.find('h1',
                                                                                     class_='single-title') else "NA"
    author = soup.find('meta', property='twitter:data1')['content'] if soup.find('meta',
                                                                                 property='twitter:data1') else "NA"
    published_date = soup.find('time', class_='single-meta-date')['datetime'] if soup.find('time',
                                                                                           class_='single-meta-date') else "NA"
    topics = [tag['content'] for tag in soup.find_all('meta', property='article:tag')] if soup.find_all('meta',
                                                                                                        property='article:tag') else [
        "NA"]

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "created_at": published_date,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


# Driver code
url = url
filename = filename
main(url=url, filename=filename)
