import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

DATA_DIR = os.getenv('DATA_DIR', '.')
INDEX_NAME = os.getenv("INDEX")
CLOUD_ID = os.getenv("CLOUD_ID", None)
API_KEY = os.getenv("USER_PASSWORD", None)
ES_LOCAL_URL = os.getenv("ES_LOCAL_URL", None)
START_INDEX = os.getenv("START_INDEX", 0)

ES: Elasticsearch

if ES_LOCAL_URL is not None:
    ES = Elasticsearch(ES_LOCAL_URL)
elif API_KEY is not None and CLOUD_ID is not None:
    ES = Elasticsearch(
        cloud_id=CLOUD_ID,
        api_key=API_KEY,
    )

