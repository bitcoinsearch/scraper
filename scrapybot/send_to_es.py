from elasticsearch import Elasticsearch, helpers
from elasticsearch import Elasticsearch
from datetime import datetime
import configparser
import json


config = configparser.ConfigParser()
config.read("example.ini")

# Open the JSON file and load its contents
with open("bolts.json", "r") as file:
    docs = json.load(file)
config.read("example.ini")

es = Elasticsearch(
    cloud_id=config["ELASTIC"]["cloud_id"],
    basic_auth=(config["ELASTIC"]["user"], config["ELASTIC"]["password"]),
)


# datum = datetime.utcnow().isoformat()
# river =  {"id": "river-glossary-7a1448e3-6896-457d-a202-e825dd1db35c",
#           "title": "Yield Curve",
#           "body": "A yield curve is a line that plots  predictor of an economic transition.",
#           "body_type": "raw",
#           "authors": [],
#           "domain": "https://river.com",
#           "url": "https://river.com/learn/terms/y/yield-curve/",
#           "created_at": datum}

# es.index(
#  index='bitcoin-search-april-23',
#  document=river)

result = es.search(index=config["ELASTIC"]["index"], query={"match_all": {}})

wanted = result["hits"]["total"]
print(wanted)

# result = es.search(
#     index="bitcoin-search-june-23", query={"match": {"id": "masteringln"}}
# )


# wanted = result["hits"]["hits"]
# print(wanted)
