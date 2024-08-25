import json

import requests
from bs4 import BeautifulSoup


def main(url, filename):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string if soup.title else "NA"
    author = "NA"
    published_date = "NA"
    topics = []

    # Extract author and published date from the content
    author_tag = soup.find('b', title=lambda x: x and 'View the profile of' in x)
    if author_tag:
        author = author_tag.text.strip()

    date_tag = soup.find('span', class_='smalltext')
    if date_tag:
        published_date = date_tag.text.strip()

    # Extract topics from the navigation
    nav_links = soup.find_all('a', class_='nav')
    for link in nav_links:
        if link.text and link.text not in topics:
            topics.append(link.text.strip())

    # Prepare the JSON object
    output = {
        "title": title,
        "author": author,
        "published_date": published_date,
        "topics": topics
    }

    # Write to JSON file
    with open(filename, 'w') as json_file:
        json.dump(output, json_file, ensure_ascii=False, indent=4)


# Driver code
main(url='https://bitcointalk.org/index.php?topic=935898.0', filename=filename)
