import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    data = {
        "title": None,
        "author": None,
        "published_date": None,
        "created_at": None,
        "topics": [],
        "question": None,
        "question_content": None,
        "answers": [],
        "answer_votes": None,
        "comments": None,
        "user_statistics": None
    }

    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        data["title"] = title_tag.string.strip()

    author_tag = soup.find('meta', attrs={'name': 'author'})
    if author_tag and 'content' in author_tag.attrs:
        data["author"] = author_tag['content'].strip()

    published_date_tag = soup.find('time')
    if published_date_tag and 'datetime' in published_date_tag.attrs:
        data["published_date"] = published_date_tag['datetime'].strip()

    question_tag = soup.find('div', class_='quest')
    if question_tag:
        paragraphs = question_tag.find_all('p')
        data["question"] = paragraphs[0].get_text(strip=True) if paragraphs else None
        data["question_content"] = ' '.join([p.get_text(strip=True) for p in paragraphs])

    answers_tag = soup.find('div', class_='answers')
    if answers_tag:
        answers_list = answers_tag.find_all('li')
        data["answers"] = [li.get_text(strip=True) for li in answers_list]

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


# Driver code
main(url=url, filename=filename)
