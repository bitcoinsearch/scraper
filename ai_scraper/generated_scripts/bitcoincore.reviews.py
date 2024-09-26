import requests
from bs4 import BeautifulSoup
import json

def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string.strip() if soup.title else "NA"
    author = soup.find('meta', attrs={'name': 'author'})['content'] if soup.find('meta', attrs={'name': 'author'}) else "NA"
    published_date = "NA"
    topics = []

    recent_meetings = soup.find_all('tr')
    for meeting in recent_meetings:
        date = meeting.find('td', class_='Home-posts-post-date')
        if date:
            published_date = date.text.strip()
            break

    topics = ["Bitcoin Core", "PR Review Club"]

    output = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "created_at": published_date,
        "topics": topics
    }

    with open(filename, 'w') as f:
        json.dump(output, f, indent=4)

main(url=globals().get('url'), filename=globals().get('filename'))