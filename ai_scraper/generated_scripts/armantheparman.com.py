import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('h1', class_='entry-title').get_text(strip=True) if soup.find('h1',
                                                                                    class_='entry-title') else "NA"
    author = "NA"  # Author not explicitly mentioned in the provided content
    published_date = soup.find('meta', property='article:published_time')['content'] if soup.find('meta',
                                                                                                  property='article:published_time') else "NA"
    created_at = published_date  # Assuming created_at is the same as published_date
    topics = ["Bitcoin", "Transactions", "OP_RETURN"]  # Example topics based on content

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "created_at": created_at,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


# Driver code
main(url=globals().get('url'), filename=globals().get('filename'))
