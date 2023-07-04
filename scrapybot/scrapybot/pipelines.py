# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import configparser
from elasticsearch import Elasticsearch

config = configparser.ConfigParser()
config.read("config.ini")

es = Elasticsearch(
    cloud_id=config["ELASTIC"]["cloud_id"],
    basic_auth=(config["ELASTIC"]["user"], config["ELASTIC"]["password"]),
)


class ElasticsearchPipeline:
    def process_item(self, item, spider):
        # Index the item in Elasticsearch
        es.index(index=config["ELASTIC"]["index"], document=item)

        return item
