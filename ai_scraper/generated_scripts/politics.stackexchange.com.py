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
    question_content = ' '.join(
        [p.text.strip() for p in soup.find('div', class_='s-prose js-post-body', itemprop='text').find_all('p')])

    answers = []
    accepted_answer = None
    highest_voted_ans = None
    accepted_answer_indicator_exists = False

    for answer in soup.find_all('div', class_='answer'):
        answer_content = ' '.join(
            [p.text.strip() for p in answer.find('div', class_='s-prose js-post-body', itemprop='text').find_all('p')])
        answers.append(answer_content)

        if 'accepted-answer' in answer['class'] or 'js-accepted-answer' in answer['class']:
            accepted_answer = answer_content
            accepted_answer_indicator_exists = True

        if highest_voted_ans is None or int(answer['data-score']) > int(highest_voted_ans['score']):
            highest_voted_ans = {'content': answer_content, 'score': answer['data-score']}

    comments = []
    for comment in soup.find_all('div', class_='comment'):
        comment_text = comment.find('span', class_='comment-copy').text.strip()
        comments.append(comment_text)

    user_statistics = {
        "author": author,
        "reputation": soup.find('span', class_='reputation-score').text.strip()
    }

    output = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "question": question,
        "question_content": question_content,
        "answers": answers,
        "accepted_answer_indicator_exists": accepted_answer_indicator_exists,
        "accepted_answer": accepted_answer,
        "highest_voted_ans": highest_voted_ans,
        "comments": comments,
        "user_statistics": user_statistics
    }

    with open(filename, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)


# Driver code
main(url=url, filename=filename)
