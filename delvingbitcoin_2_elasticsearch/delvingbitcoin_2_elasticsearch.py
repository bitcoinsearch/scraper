import os
import json
from elastic import create_index, document_add, document_view


# Get environment variables for path and index name
INDEX = os.getenv("INDEX") or "delvingbitcoin"
ARCHIVE = os.getenv("ARCHIVE") or "archive"
SUB_ARCHIVE = os.getenv("SUB_ARCHIVE") or "posts"

# Create Index if it doesn't exist
if create_index(INDEX):
    print(f"Index: {INDEX}, created successfully.")
else:
    print(f"Index: {INDEX}, already exist.")

# Get the directory where the Python script is located
script_dir = os.path.dirname(os.path.realpath(__file__))

# Specify the path to the folder containing JSON files
folder_path = os.path.join(script_dir, ARCHIVE, SUB_ARCHIVE)


def index_documents(files_path):
    # Iterate through files in the specified path
    for root, dirs, files in os.walk(files_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                print(f'Indexing document from {file_path}')

                # Load JSON data from file
                with open(file_path, 'r', encoding='utf-8') as json_file:
                    document = json.load(json_file)

                # Select required fields
                doc = {
                    'id': document['id'],
                    'authors': document['username'],
                    'title': document['topic_title'],
                    'body': document['raw'],
                    'body_type': 'raw',
                    'created_at': document['updated_at'],
                    'domain': "https://delvingbitcoin.org/",
                    'url': f"https://delvingbitcoin.org/t/{document['topic_slug']}/{document['topic_id']}",
                }

                # Check if document already exist
                resp = document_view(index_name="djv", doc_id=doc['id'])
                if not resp:
                    # If not, create document
                    resp = document_add(index_name="djv", doc=doc, doc_id=doc['id'])
                    print(f'Successfully added {doc["title"]} with the id: {doc["id"]}, Info: {resp}.')
                else:
                    print(f"Document with id: {doc['id']} already exist.")


if __name__ == "__main__":
    index_documents(folder_path)
    print(f'{("-" * 20)}DONE{("-" * 20)}')
