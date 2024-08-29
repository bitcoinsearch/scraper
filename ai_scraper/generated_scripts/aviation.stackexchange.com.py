import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('h1', class_='fs-headline1').get_text(strip=True)
    author = soup.find('div', class_='user-info').find('a').get_text(strip=True)
    published_date = soup.find('time', itemprop='dateCreated')['datetime']
    question_content = soup.find('div', class_='s-prose js-post-body').get_text(separator=' ', strip=True)

    answers = []
    accepted_answer = None
    accepted_answer_indicator_exists = False

    for answer in soup.find_all('div', class_='answer'):
        answer_content = answer.find('div', class_='s-prose js-post-body').get_text(separator=' ', strip=True)
        answers.append(answer_content)

        if 'accepted-answer' in answer.get('class', []) or 'js-accepted-answer' in answer.get('class', []):
            accepted_answer = answer_content
            accepted_answer_indicator_exists = True

    comments = []
    for comment in soup.find_all('div', class_='comment'):
        comment_text = comment.find('span', class_='comment-copy').get_text(strip=True)
        comments.append(comment_text)

    user_statistics = {
        "author": author,
        "reputation": soup.find('span', class_='reputation-score').get_text(strip=True)
    }

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "question": question_content,
        "answers": answers,
        "accepted_answer_indicator_exists": accepted_answer_indicator_exists,
        "accepted_answer": accepted_answer,
        "comments": comments,
        "user_statistics": user_statistics
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


# Driver code
main(url=url, filename=filename)
