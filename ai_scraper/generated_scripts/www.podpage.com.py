import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find('h1', class_='heading heading-2 strong-400 text-normal mb-4').get_text(strip=True)
    author = "BitcoinQ_A"  # Author is mentioned in the content
    published_date = soup.find('div',
                               class_='text-uppercase c-text-light strong-300 mb-1 content-publish-date').get_text(
        strip=True)

    topics = "bitcoin for beginners, acquiring bitcoin, tradeoffs, dangers of KYC, holding your own keys, using your own node, transaction fees, utxo management and labeling, coinjoin, lightning, multisig, common mistakes and questions"

    question_content = soup.find('div', class_='block-body block-post-body').get_text(separator=' ', strip=True)

    answers = [
        "support dispatch: https://citadeldispatch.com/contribute",
        "EPISODE: 43",
        "BLOCK: 708970",
        "PRICE: 1501 sats per dollar",
        f"TOPICS: {topics}",
        "@BitcoinQ_A: https://twitter.com/BitcoinQ_A"
    ]

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "topics": topics,
        "question": question_content,
        "answers": answers
    }

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


# Driver code
main(url=url, filename=filename)
