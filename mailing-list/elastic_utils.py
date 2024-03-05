import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, NotFoundError, BadRequestError
from loguru import logger
load_dotenv()

es = Elasticsearch(
    cloud_id=os.getenv("CLOUD_ID"),
    api_key=os.getenv("USER_PASSWORD")
)


def create_index(index_name):
    """Functionality to create index."""
    try:
        resp = es.indices.create(index=index_name)
    except BadRequestError:
        resp = False
    return resp


def document_add(index_name, doc, doc_id=None):
    """Funtion to add a document by providing index_name,
    document type, document contents as doc and document id."""
    resp = es.index(index=index_name, body=doc, id=doc_id)
    return resp


def document_view(index_name, doc_id):
    """Function to view document."""
    try:
        resp = es.get(index=index_name, id=doc_id)
    except NotFoundError:
        resp = False
    return resp


def document_update(index_name, doc_id, doc=None, new=None):
    """Function to edit a document either updating existing fields or adding a new field."""
    if doc:
        resp = es.index(index=index_name, id=doc_id, body=doc)
    else:
        resp = es.update(index=index_name, id=doc_id, body={"doc": new})
    return resp


def document_delete(index_name, doc_id, verbose=False):
    """Function to delete a specific document."""
    resp = es.delete(index=index_name, id=doc_id)
    if verbose:
        logger.info(resp)
    return resp


def delete_index(index_name):
    """Delete an index by specifying the index name"""
    resp = es.indices.delete(index=index_name)
    return resp


def document_exist(index_name, doc_id):
    body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "term": {
                            "id.keyword": doc_id
                        }
                    }
                ]
            }
        }
    }

    resp = es.count(index=index_name, body=body)

    return resp["count"] > 0
