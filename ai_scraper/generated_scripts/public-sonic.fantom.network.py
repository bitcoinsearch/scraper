import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string if soup.title else "NA"
    author = "NA"
    published_date = "NA"
    question = "NA"
    question_content = "NA"
    answers = []

    # Extracting author and published date if available
    author_tag = soup.find('meta', property='og:description')
    if author_tag:
        author = author_tag['content']

    published_date_tag = soup.find('meta', property='og:title')
    if published_date_tag:
        published_date = published_date_tag['content']

    # Extracting question and answers
    question_tag = soup.find('div', class_='quest')
    if question_tag:
        question_content = ' '.join([p.get_text() for p in question_tag.find_all('p')])
        question = question_content.split('.')[0]  # Assuming the first sentence is the question

    answers_tags = soup.find_all('li')
    for answer_tag in answers_tags:
        answers.append(answer_tag.get_text(strip=True))

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "question": question,
        "question_content": question_content,
        "answers": answers
    }

    with open(filename, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# Driver code
main(url=url, filename=filename)
