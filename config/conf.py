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

# Get ES_URL from environment for URL-based connections
ES_URL = os.getenv("ES_URL", None)

if ES_LOCAL_URL is not None:
    ES = Elasticsearch(ES_LOCAL_URL)
elif ES_URL is not None and API_KEY is not None:
    # Use URL-based connection with API key in headers format
    ES = Elasticsearch(
        ES_URL,
        headers={'Authorization': f'ApiKey {API_KEY}'},
        request_timeout=30
    )
elif API_KEY is not None and CLOUD_ID is not None:
    ES = Elasticsearch(
        cloud_id=CLOUD_ID,
        api_key=API_KEY,
    )

