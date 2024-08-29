import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('title').text.strip()
    author = soup.find('div', class_='user-info').find('a').text.strip()
    published_date = soup.find('time', itemprop='dateCreated')['datetime']
    question = soup.find('h1', class_='fs-headline1').text.strip()
    question_content = ' '.join([p.text.strip() for p in soup.find('div', class_='s-prose js-post-body').find_all('p')])

    answers = []
    accepted_answer = None
    accepted_answer_indicator_exists = False

    for answer in soup.find_all('div', class_='answer'):
        answer_content = ' '.join(
            [p.text.strip() for p in answer.find('div', class_='s-prose js-post-body').find_all('p')])
        answers.append(answer_content)

        if 'accepted-answer' in answer['class'] or 'js-accepted-answer' in answer['class']:
            accepted_answer = answer_content
            accepted_answer_indicator_exists = True

    user_statistics = {
        "author": author,
        "reputation": soup.find('span', class_='reputation-score')['title'] if soup.find('span',
                                                                                         class_='reputation-score') else 'NA',
        "badges": {
            "gold": soup.find('span', title='gold badges')['aria-hidden'] if soup.find('span',
                                                                                       title='gold badges') else '0',
            "silver": soup.find('span', title='silver badges')['aria-hidden'] if soup.find('span',
                                                                                           title='silver badges') else '0',
            "bronze": soup.find('span', title='bronze badges')['aria-hidden'] if soup.find('span',
                                                                                           title='bronze badges') else '0'
        }
    }

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "question": question,
        "question_content": question_content,
        "answers": answers,
        "accepted_answer_indicator_exists": accepted_answer_indicator_exists,
        "accepted_answer": accepted_answer,
        "highest_voted_answer": answers[0] if answers else None,
        "comments": [],  # Assuming no comments are extracted in this context
        "user_statistics": user_statistics
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


# Driver code
url = url
filename = filename
main(url=url, filename=filename)
