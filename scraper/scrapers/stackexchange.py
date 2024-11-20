from datetime import datetime, timedelta, timezone
import re
import html
import traceback
import json

import requests
from loguru import logger
from bs4 import BeautifulSoup
from scraper.outputs.elasticsearch_output import ElasticsearchOutput
from scraper.registry import scraper_registry

@scraper_registry.register("StackExchange")

class StackExchangeScraper:
    """Scraper for retrieving and processing posts from Bitcoin StackExchange."""
    def __init__(self):
        # Get the current timestamp
        current_timestamp = datetime.now()
        # Calculate the timestamp from 7 days before
        seven_days_ago = current_timestamp - timedelta(days=7)

        # Convert timestamps to Unix timestamps
        from_timestamp = int(seven_days_ago.timestamp())
        to_timestamp = int(current_timestamp.timestamp())
        
        #!6WPIomnA_rhBb Get titles and body, and body_markdown filter
        self.page = 1
        self.pagesize = 100
        self.total_pages = 1
        self.api_url = f"https://api.stackexchange.com/posts?site=bitcoin.stackexchange&filter=!6WPIomnA_rhBb&fromdate={from_timestamp}&todate={to_timestamp}&page={self.page}&pagesize={self.pagesize}"
        self.total_url = f"https://api.stackexchange.com/posts?site=bitcoin.stackexchange&filter=total&fromdate={from_timestamp}&todate={to_timestamp}"
        self.total_documents = 0
        self.posts = []
        self.link_property = "link"
        self.data_property = "items"

    def get_json(self):
        """Fetch and parse JSON data from the StackExchange API.
        
        Retrieves posts from the API and stores them in self.posts.
        """
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            # Get total number of documents

            response = requests.get(self.total_url, headers=headers, timeout=90)
            response.raise_for_status()  

            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                data = response.json()
                self.total_documents = data.get("total")

                # Calculate the number of pages
                total_pages = round(self.total_documents / self.pagesize)

                if total_pages == 0:
                    self.total_pages = 1
                else:
                    self.total_pages = total_pages


            # Loop through all pages    
            for page in range(1, self.total_pages + 1):
                self.page = page
                
                # Get posts
                response = requests.get(self.api_url, headers=headers, timeout=90)
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

                    # Append posts to self.posts
                    self.posts.extend(posts_array)
                else:
                    print(f"Failed to retrieve data. Status code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download the repo: {e}")
        except json.JSONDecodeError:
            print("Failed to parse JSON response.")
        except (ValueError, TypeError) as e:
            print(f"Error processing data: {e}")
            print(f"Error processing data: {e}")

    async def format_data(self):
        """Format and store StackExchange posts in Elasticsearch.
        
        Processes each post, extracts relevant information, and stores it in Elasticsearch
        if it doesn't already exist.
        """
        try:
            output = ElasticsearchOutput()
            await output.initialize()

            for post in self.posts:
                url = post.get(self.link_property)
                owner = post.get("owner")
                author = owner.get("display_name")
                creation_date = post.get("creation_date")
                body = self.clean_html(post.get("body_markdown"))
                p_id = post.get("post_id")
                post_id = f"stackexchange-{p_id}" 
                post_type = post.get("post_type")
                title = post.get("title")

                response = requests.get(url, timeout=60)

                soup = BeautifulSoup(response.text, "html.parser")

                # Extract accepted answer ID if available
                accepted_answer_element = soup.find("div", {"itemprop": "acceptedAnswer"})
                accepted_answer_id = accepted_answer_element["data-answerid"] if accepted_answer_element else None

                # Extract tags
                tags = [tag.text for tag in soup.find_all("a", {"class": "post-tag"})]

                base_url = "https://bitcoin.stackexchange.com"

                document = {}

                if post_type == "question":
                    document = {
                        "title": title,
                        "body": body,
                        "body_type": "raw",
                        "authors": [author],
                        "id": post_id,
                        "tags": tags,
                        "domain": base_url,
                        "url": url,
                        "thread_url":  url,
                        "created_at": creation_date,
                        "accepted_answer_id": accepted_answer_id,
                        "type": "question",
                        "indexed_at": datetime.now(timezone.utc).isoformat()
                    }
                elif post_type == "answer":
                    question_link = soup.find("a", class_="question-hyperlink")['href']
                    url = base_url + question_link

                    document = {
                        "title": title,
                        "body": body,
                        "body_type": "raw",
                        "authors": [author],
                        "id": post_id,
                        "tags": tags,
                        "domain": base_url,
                        "url": url,
                        "thread_url": url,
                        "created_at": creation_date,
                        "accepted_answer_id": accepted_answer_id,
                        "type": "question",
                        "indexed_at": datetime.now(timezone.utc).isoformat()
                    }

                # insert the doc if it doesn't exist, with '_id' set by our logic
                resp = await output.get_metadata(config=document)
                if not resp:
                    _ = await output.update_metadata(document)
                    logger.success(f"Added! ID: {document['id']}, Title: {document['title']}")
                else:
                    pass

        except requests.RequestException as ex:
            logger.error(f"Request error occurred: {ex} \n{traceback.format_exc()}")
        except BeautifulSoup.ParserError as ex:
            logger.error(f"Parsing error occurred: {ex} \n{traceback.format_exc()}")
        except (KeyError, AttributeError) as ex:
            logger.error(f"Data extraction error occurred: {ex} \n{traceback.format_exc()}")

        logger.info("All Documents updated successfully!")

    @staticmethod
    def clean_html(text: str):
        """Clean HTML text by removing tags and converting escape sequences.

        Args:
            text (str): The HTML text to clean

        Returns:
            str: The cleaned text
        """

        # Convert Unicode escape sequences to readable text
        text = text.encode().decode('unicode_escape')
        
        # Remove HTML tags using regex
        clean_text = re.sub(r'<.*?>', '', text)
        
        # Unescape any HTML entities (like &lt; &gt;)
        clean_text = html.unescape(clean_text)
        
        return clean_text

