import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('h1', class_='post-title').get_text(strip=True)
    author = soup.find('meta', attrs={'name': 'author'})['content']
    published_date = soup.find('time', class_='dt-published')['datetime']

    question_content = soup.find('div', class_='post-content').get_text(separator=' ', strip=True)

    answers = []
    for li in soup.select('ul > li'):
        answers.append(li.get_text(separator=' ', strip=True))

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "question": question_content,
        "answers": answers
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


main(url=globals().get('url'), filename=globals().get('filename'))
