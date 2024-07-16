import os

from dotenv import load_dotenv
from elasticsearch import BadRequestError
from elasticsearch import Elasticsearch, NotFoundError
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
    """Function to add a document by providing index_name,
    document type, document contents as doc and document id."""
    resp = es.index(index=index_name, body=doc, id=doc_id)
    return resp


def document_view(index_name, doc_id):
    """Function to view a document."""
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


def upsert_document(index_name, doc_id, doc_body):
    """
    Upserts a document into the specified Elasticsearch index.

    Args:
        es (Elasticsearch): The Elasticsearch client instance.
        index_name (str): The name of the Elasticsearch index.
        doc_id (str): The ID of the document.
        doc_body (dict): The body of the document containing fields to insert or update.

    Returns:
        dict: Response from Elasticsearch.
    """
    # Script for updating only provided fields
    script = {
        "source": "ctx._source.putAll(params)",
        "params": doc_body
    }

    # Complete request body including the script and the upsert document
    request_body = {
        "scripted_upsert": True,
        "script": script,
        "upsert": doc_body
    }

    # Perform the upsert operation
    response = es.update(index=index_name, id=doc_id, body=request_body)
    return response


def fetch_data_based_on_domain(index, domain):
    logger.info(f"looking for URL: {domain}")
    output_list = []

    if es.ping():
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "term":
                                {
                                    "domain.keyword": str(domain)
                                }
                        }
                    ]
                }
            }
        }

        # Initialize the scroll
        scroll_response = es.search(index=index, body=query, size=10000, scroll='5m')
        scroll_id = scroll_response['_scroll_id']
        results = scroll_response['hits']['hits']

        while len(results) > 0:
            for result in results:
                output_list.append(result)

            # Fetch the next batch of results
            scroll_response = es.scroll(scroll_id=scroll_id, scroll='5m')
            scroll_id = scroll_response['_scroll_id']
            results = scroll_response['hits']['hits']
        return output_list
    else:
        logger.warning('Could not connect to Elasticsearch')
        return None
