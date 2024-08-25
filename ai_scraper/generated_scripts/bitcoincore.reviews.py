import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string.strip() if soup.title else "NA"
    author = soup.find('meta', attrs={'name': 'author'})['content'] if soup.find('meta',
                                                                                 attrs={'name': 'author'}) else "NA"
    published_date = "NA"
    topics = []

    recent_meetings = soup.find_all('tr')
    for meeting in recent_meetings:
        date = meeting.find('td', class_='Home-posts-post-date')
        if date:
            published_date = date.text.strip()
        topic = meeting.find('a', class_='Home-posts-post-title')
        if topic:
            topics.append(topic.text.strip())

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "topics": topics
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


# Driver code
main(url=url, filename=filename)
