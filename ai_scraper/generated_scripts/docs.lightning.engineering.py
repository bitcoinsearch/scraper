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

    # Extract author and published date if available
    author_meta = soup.find('meta', {'name': 'author'})
    if author_meta and 'content' in author_meta.attrs:
        author = author_meta['content']

    published_meta = soup.find('meta', {'name': 'date'})
    if published_meta and 'content' in published_meta.attrs:
        published_date = published_meta['content']

    # Extract question and content
    question_div = soup.find('div', class_='quest')
    if question_div:
        question_paragraphs = question_div.find_all('p')
        question = " ".join([p.get_text(strip=True) for p in question_paragraphs])
        question_content = question

    # Extract answers
    answers_div = soup.find('div', class_='answers')
    if answers_div:
        answer_items = answers_div.find_all('li')
        answers = [item.get_text(strip=True) for item in answer_items]

    # Create JSON object
    output = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "question": question,
        "question_content": question_content,
        "answers": answers
    }

    # Write to JSON file
    with open(filename, 'w') as json_file:
        json.dump(output, json_file, ensure_ascii=False, indent=4)


# Driver code
main(url=globals().get('url'), filename=globals().get('filename'))
