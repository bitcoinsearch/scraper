import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('title').text if soup.find('title') else "NA"
    author = soup.find('meta', {'name': 'twitter:data1'}).get('content', "NA") if soup.find('meta', {
        'name': 'twitter:data1'}) else "NA"
    published_date = soup.find('meta', {'property': 'article:published_time'}).get('content', "NA") if soup.find('meta',
                                                                                                                 {
                                                                                                                     'property': 'article:published_time'}) else "NA"
    topics = [tag.get('content') for tag in soup.find_all('meta', {'property': 'article:tag'})]

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


main(url=globals().get('url'), filename=globals().get('filename'))
