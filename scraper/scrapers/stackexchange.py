from datetime import datetime, timezone

import requests
from loguru import logger
import json
from bs4 import BeautifulSoup


class StackExchangeScraper:
    def __init__(self, api_url, link_property, data_property):
        self.api_url = api_url
        self.posts = []
        self.link_property = link_property
        self.data_property = data_property

    def get_json(self):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(self.api_url, headers=headers)
            response.raise_for_status()  # Raise an HTTPError if the response status is 4xx or 5xx

            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                data = response.json()

                # Filter only the required fields (links)
                if self.data_property is not None:
                    posts_array = [
                        item
                        for item in data.get(self.data_property, [])
                    ]
                else:
                    posts_array = [
                        item
                        for item in data
                    ]

                self.posts = posts_array
            else:
                print(f"Failed to retrieve data. Status code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download the repo: {e}")
        except json.JSONDecodeError:
            print("Failed to parse JSON response.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def scrape_data(self):
        for post in self.posts:
            url = post.get(self.link_property)
            owner = post.get("owner")
            author = owner.get("display_name")
            creation_date = post.get("creation_date")
            id = "stackexchange-" + post.get("post_id")

            response = requests.get(url)

            soup = BeautifulSoup(response.text, "html.parser")

            # Step 2: Extract title, author, body, and creation date
            title = soup.find("a", {"class": "question-hyperlink"}).text
            body = soup.find("div", {"class": "s-prose js-post-body"}).text

            # Extract accepted answer ID if available
            accepted_answer_element = soup.find("div", {"itemprop": "acceptedAnswer"})
            accepted_answer_id = accepted_answer_element["data-answerid"] if accepted_answer_element else None

            # Extract tags
            tags = [tag.text for tag in soup.find_all("a", {"class": "post-tag"})]

            document = {
                "title": title,
                "body": body,
                "body_type": "raw",
                "authors": [author],
                "id": id,
                "tags": tags,
                "domain": "https://bitcoin.stackexchange.com",
                "url": url,
                "thread_url":  url,
                "created_at": creation_date,
                "accepted_answer_id": accepted_answer_id,
                "type": "question",
                "indexed_at": datetime.now(timezone.utc).isoformat()
            }








