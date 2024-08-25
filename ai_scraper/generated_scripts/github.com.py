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
        "answer_votes": [],
        "comments": [],
        "user_statistics": {}
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

    created_at_tag = soup.find('meta', attrs={'name': 'date'})
    if created_at_tag and 'content' in created_at_tag.attrs:
        data["created_at"] = created_at_tag['content'].strip()

    question_tag = soup.find('div', class_='quest')
    if question_tag:
        paragraphs = question_tag.find_all('p')
        data["question"] = paragraphs[0].get_text(strip=True) if paragraphs else None
        data["question_content"] = ' '.join([p.get_text(strip=True) for p in paragraphs])

    answers_tag = soup.find('div', class_='answers')
    if answers_tag:
        answers_list = answers_tag.find_all('li')
        data["answers"] = [answer.get_text(strip=True) for answer in answers_list]

    # Assuming answer votes, comments, and user statistics are in specific tags
    # These are placeholders as the actual HTML structure is not provided
    # You would need to adjust these based on the actual HTML structure
    data["answer_votes"] = []  # Placeholder for answer votes extraction
    data["comments"] = []  # Placeholder for comments extraction
    data["user_statistics"] = {}  # Placeholder for user statistics extraction

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


# Driver code
main(url=url, filename=filename)
