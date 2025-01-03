import os
import sys
import time

from elasticsearch import BadRequestError
from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.exceptions import ConflictError
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conf import ES

def create_index(index_name):
    """Functionality to create index."""
    try:
        resp = ES.indices.create(index=index_name)
    except BadRequestError:
        resp = False
    return resp


def document_add(index_name, doc, doc_id=None):
    """Function to add a document by providing index_name,
    document type, document contents as doc and document id."""
    resp = ES.index(index=index_name, body=doc, id=doc_id)
    return resp


def document_view(index_name, doc_id):
    """Function to view a document."""
    try:
        resp = ES.get(index=index_name, id=doc_id)
    except NotFoundError:
        resp = False
    return resp


def document_update(index_name, doc_id, doc=None, new=None):
    """Function to edit a document either updating existing fields or adding a new field."""
    if doc:
        resp = ES.index(index=index_name, id=doc_id, body=doc)
    else:
        resp = ES.update(index=index_name, id=doc_id, body={"doc": new})
    return resp


def document_delete(index_name, doc_id, verbose=False):
    """Function to delete a specific document."""
    resp = ES.delete(index=index_name, id=doc_id)
    if verbose:
        logger.info(resp)
    return resp


def delete_index(index_name):
    """Delete an index by specifying the index name"""
    resp = ES.indices.delete(index=index_name)
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
    resp = ES.count(index=index_name, body=body)
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
    response = ES.update(index=index_name, id=doc_id, body=request_body)
    return response


def update_authors_names_from_es(index, old_author, new_author, max_retries=3, retry_delay=2):
    if es.ping():
        script = {
            "source": f"""
                for (int i = 0; i < ctx._source.authors.size(); i++) {{
                    if (ctx._source.authors[i] == '{old_author}') {{
                        ctx._source.authors[i] = '{new_author}';
                    }}
                }}
            """
        }

        query = {
            "bool": {
                "must": [
                    {
                        "term": {
                            "authors.keyword": old_author
                        }
                    }
                ]
            }
        }

        attempt = 0
        while attempt < max_retries:
            try:
                response = ES.update_by_query(
                    index=index,
                    body={
                        "script": script,
                        "query": query
                    }
                )
                logger.success(f"Updated {response['total']} documents: '{old_author}' --> '{new_author}'")
                return response
            except ConflictError as ex:
                attempt += 1
                if attempt < max_retries:
                    logger.warning(f"Version conflict occurred. Retry {attempt}/{max_retries}...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to update documents after {max_retries} retries: {ex}")
                    raise
    else:
        logger.warning('Could not connect to Elasticsearch')
        return None
