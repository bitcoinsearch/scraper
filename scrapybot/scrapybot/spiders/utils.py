from io import StringIO
import re
from bs4 import BeautifulSoup
from html.parser import HTMLParser
from datetime import datetime


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def get_details(details: list):
    result_dict = {}

    for item in details:
        if ": " in item:
            key, value = item.split(": ", 1)
            if key == "Author":
                value = re.sub(r"<[^>]+>", "", value)

            result_dict[key.strip()] = value.strip()
        else:
            print(f"Ignoring item: {item}")
    return result_dict


def strip_attributes(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all():
        tag.attrs = {}
    return str(soup)


def convert_to_iso_datetime(datetime_str):
    try:
        datetime_obj = datetime.fromisoformat(datetime_str)
        iso_datetime_str = datetime_obj.isoformat()
        return iso_datetime_str
    except ValueError:
        raise ValueError("Invalid datetime format")
