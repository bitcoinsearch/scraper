import os
from elasticsearch import Elasticsearch, NotFoundError, BadRequestError


# Get environment variables for Elasticsearch host
HOST = os.getenv("HOST") or "localhost"
PORT = os.getenv("PORT") or 9200
SCHEME = os.getenv("SCHEME") or "http"

# create an instance of elasticsearch and assign it to port 9200
ES_HOST = {"host": HOST, "port": PORT, "scheme": SCHEME}
es = Elasticsearch(hosts=[ES_HOST], verify_certs=False)


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


def document_delete(index_name, doc_id):
    """Function to delete a specific document."""
    resp = es.delete(index=index_name, id=doc_id)
    return resp


def delete_index(index_name):
    """Delete an index by specifying the index name"""
    resp = es.indices.delete(index=index_name)
    return resp
