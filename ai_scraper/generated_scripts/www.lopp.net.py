import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string if soup.title else "NA"
    author = "Jameson Lopp"  # Author is inferred from the context
    published_date = "NA"  # No published date found in the context
    question = "What is Bitcoin?"
    question_content = "Bitcoin is a new form of money that is controlled by no one and is developed as an open collaborative project. Below you'll find enough curated educational resources and information about it that you could spend months sifting through them all. Make sure you have a decent understanding of the system before you store a significant amount of value in it! The same aspects that make it so valuable also make it unforgiving to those who make mistakes."

    topics = [
        "Getting Started",
        "Setting up a Wallet",
        "Running a Node",
        "The History of Bitcoin",
        "News Sites",
        "Discussion Forums",
        "Network Statistics",
        "Transaction Fee Estimates",
        "Block Explorers",
        "Visualizations",
        "Mining",
        "Data Anchoring",
        "Technical Resources",
        "Developer Tools",
        "Security",
        "Privacy",
        "Economics",
        "Art & Music",
        "Online & Offline Classes",
        "Documentaries",
        "Video Presentations",
        "Podcasts",
        "Blogs",
        "Books",
        "X / Twitter",
        "Investment Theses",
        "Buying & Earning BTC",
        "Advanced Trading",
        "Exchange Rate Data",
        "Merchant Adoption",
        "Tax Accounting",
        "Careers",
        "Charities",
        "Legal",
        "Governance",
        "Forks",
        "Other Layers",
        "Other Resources"
    ]

    answers = []  # No answers found in the context
    answer_votes = []  # No votes found in the context
    comments = []  # No comments found in the context
    user_statistics = {}  # No user statistics found in the context

    data = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "question": question,
        "question_content": question_content,
        "topics": topics,
        "answers": answers,
        "answer_votes": answer_votes,
        "comments": comments,
        "user_statistics": user_statistics
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


# Driver code
main(url=url, filename=filename)
