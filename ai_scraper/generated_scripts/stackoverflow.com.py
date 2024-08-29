import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('title').text.strip()
    author = soup.find('a', class_='user-details').text.strip() if soup.find('a', class_='user-details') else "NA"
    published_date = soup.find('time', itemprop='dateCreated')['datetime'] if soup.find('time',
                                                                                        itemprop='dateCreated') else "NA"
    question_content = ' '.join([p.text.strip() for p in soup.find('div', class_='s-prose js-post-body').find_all('p')])

    answers = []
    accepted_answer = None
    highest_voted_answer = None
    accepted_answer_indicator_exists = False

    for answer in soup.find_all('div', class_='answer'):
        answer_content = answer.find('div', class_='s-prose js-post-body').text.strip()
        answers.append(answer_content)

        if 'accepted-answer' in answer['class'] or 'js-accepted-answer' in answer['class']:
            accepted_answer = answer_content
            accepted_answer_indicator_exists = True

        if highest_voted_answer is None or int(answer['data-score']) > int(highest_voted_answer['data-score']):
            highest_voted_answer = answer

    comments = []
    for comment in soup.find_all('div', class_='comment'):
        comments.append(comment.find('span', class_='comment-copy').text.strip())

    user_statistics = {
        "author_reputation": soup.find('span', class_='reputation-score')['title'] if soup.find('span',
                                                                                                class_='reputation-score') else "NA",
        "author_badges": {
            "gold": soup.find('span', title="gold badges").text if soup.find('span', title="gold badges") else "0",
            "silver": soup.find('span', title="silver badges").text if soup.find('span',
                                                                                 title="silver badges") else "0",
            "bronze": soup.find('span', title="bronze badges").text if soup.find('span', title="bronze badges") else "0"
        }
    }

    output = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "question": question_content,
        "answers": answers,
        "accepted_answer_indicator_exists": accepted_answer_indicator_exists,
        "accepted_answer": accepted_answer,
        "highest_voted_answer": highest_voted_answer['data-score'] if highest_voted_answer else "NA",
        "comments": comments,
        "user_statistics": user_statistics
    }

    with open(filename, 'w') as f:
        json.dump(output, f, indent=4)


main(url=globals().get('url'), filename=globals().get('filename'))
