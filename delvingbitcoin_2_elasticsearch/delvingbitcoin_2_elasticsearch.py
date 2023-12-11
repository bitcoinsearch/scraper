import os
import json
from dotenv import load_dotenv

# from loguru import logger
from elastic import create_index, document_add, document_exist, document_view
from achieve import download_dumps

dotenv_path = os.path.join(os.path.dirname(__file__),'..','.env')
load_dotenv(dotenv_path)

# Get environment variables for path and index name
INDEX = os.getenv("INDEX")
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
                print(f'Fetching document from {file_path}')

                # Load JSON data from file
                with open(file_path, 'r', encoding='utf-8') as json_file:
                    document = json.load(json_file)

                # Select required fields
                doc = {
                    'id': f'{document["id"]}_{document["username"]}_{document["topic_slug"]}_{document["post_number"]}',
                    'authors': document['username'],
                    'title': document['topic_title'],
                    'body': document['raw'],
                    'body_type': 'raw',
                    'created_at': document['updated_at'],
                    'domain': "https://delvingbitcoin.org/",
                    'url': f"https://delvingbitcoin.org/t/{document['topic_slug']}/{document['topic_id']}",
                }

                if document['post_number'] != 1:
                    doc['url'] += f'/{document["post_number"]}'



                # Check if document already exist
                resp = document_exist(index_name=INDEX, doc_id=doc['id'])
                if not resp:
                    # If not, create document
                    resp = document_add(index_name=INDEX, doc=doc, doc_id=doc['id'])
                    print(f'Successfully added {doc["title"]} with the id: {doc["id"]}, Info: {resp}.')
                else:
                    print(f"Document with id: {doc['id']} already exist.")


if __name__ == "__main__":
    no_new_posts = download_dumps()
    if no_new_posts == False:
        print("New Post found to update on ES!")
        index_documents(folder_path)
    else:
        print("No New Post found to update on ES!")
    print(f'{("-" * 20)}DONE{("-" * 20)}')
