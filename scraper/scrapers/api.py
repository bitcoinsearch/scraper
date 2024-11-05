import requests
from loguru import logger
import json


class JsonAPIScraper:
    def __init__(self, api_url, link_property, data_property):
        self.api_url = api_url
        self.api_links = []
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
                    links_array = [
                        item.get(self.link_property)
                        for item in data.get(self.data_property, [])
                    ]
                else:
                    links_array = [
                        item.get(self.link_property)
                        for item in data
                    ]

                self.api_links = links_array
            else:
                print(f"Failed to retrieve data. Status code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download the repo: {e}")
        except json.JSONDecodeError:
            print("Failed to parse JSON response.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


