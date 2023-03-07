from io import StringIO
from html.parser import HTMLParser
from os import getenv
from elastic_enterprise_search import AppSearch
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
load_dotenv()

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()
    
def app_search():
    return AppSearch(
        getenv("ES_URL"),
        http_auth=getenv("ES_TOKEN")
    )

def elastic_client():
    return Elasticsearch(
        cloud_id=getenv("CLOUD_ID"),
        basic_auth=(getenv("USERNAME"), getenv("PASSWORD"))
    )
