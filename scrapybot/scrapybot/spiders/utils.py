from io import StringIO
from bs4 import BeautifulSoup
from html.parser import HTMLParser


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
            result_dict[key.strip()] = value.strip()
        else:
            print(f"Ignoring item: {item}")
    return result_dict


def strip_attributes(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all():
        tag.attrs = {}
    return str(soup)

def split_on_headers(html: str, header_tags: list = ["h1", "h2"]):
    soup = BeautifulSoup(html, 'html.parser')

    # Find all header tags
    headers = [tag for tag in soup.find_all() if tag.name in header_tags]

    # Split the document into sections based on these tags
    sections = []
    for header in headers:
        section = {}

        # Use header as section title
        section['title'] = strip_tags(str(header))

        # Collect all sibling elements that follow the header and are not headers themselves
        content = []
        for elem in header.next_siblings:
            if elem.name in header_tags:
                break
            content.append(strip_tags(str(elem)))

        section['content'] = ' '.join(content)
        sections.append(section)

    return sections
