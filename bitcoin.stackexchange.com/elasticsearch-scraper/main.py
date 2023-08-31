import uuid
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from langchain.vectorstores import ElasticKnnSearch

from util import app_search, strip_tags, elastic_client
from elasticsearch.helpers import bulk
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
dir = os.getenv("DATA_DIR")

load_dotenv()
DUMP_URL = "https://archive.org/download/stackexchange/bitcoin.stackexchange.com.7z"

# download dump
def download_dump():
    r = requests.get(DUMP_URL, stream=True)
    with open(dir + "/bitcoin.stackexchange.com.7z", "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)


def upload_to_vectorstore(document: dict):
    def elastic_client() -> Elasticsearch:
        return Elasticsearch(
            cloud_id=os.getenv("CLOUD_ID"),
            api_key=os.getenv("USER_PASSWORD")
        )

    index_name = os.getenv('VECTORSTORE_INDEX')
    chunk_size = int(os.getenv('CHUNK_SIZE'))
    embed_model = os.getenv('OPENAI_EMBED_MODEL')
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name=embed_model, chunk_size=chunk_size,
        chunk_overlap=chunk_size // 10)
    embedding = OpenAIEmbeddings(model=embed_model,
                                 openai_api_key=os.getenv("OPENAI_API_KEY"))
    id_ = document.pop('id')
    documents = text_splitter.split_text(document.pop("body"))
    ids = [id_ + "_" + uuid.uuid4()] * len(documents)
    metadata = list(
        map(
            lambda chunk_no, parent_id: {
                **document,
                "parent_id": id_,
                "chunk_no": chunk_no,
            },
            range(1, len(documents) + 1),
        )
    )
    db_store = ElasticKnnSearch(index_name, embedding,
                                es_connection=elastic_client())
    uploaded_ids = db_store.add_texts(texts=documents, metadatas=metadata, ids=ids)
    assert len(uploaded_ids) == len(documents)
    print(db_store.client.info())


# extract dump
def extract_dump():
    import subprocess
    os.mkdir(dir + "/bitcoin.stackexchange.com")
    subprocess.call(["7z", "x", dir + "/bitcoin.stackexchange.com.7z", "-o" + dir + "/bitcoin.stackexchange.com"])

users = {}

def parse_users():
    import xml.etree.ElementTree as ET
    tree = ET.parse(dir + "/bitcoin.stackexchange.com/Users.xml")
    root = tree.getroot()
    for user in root:
        users[user.attrib.get("Id")] = user.attrib.get("DisplayName")

posts = {}

def parse_posts():
    import xml.etree.ElementTree as ET
    tree = ET.parse(dir + "/bitcoin.stackexchange.com/Posts.xml")
    root = tree.getroot()
    documents = []
    for post in root:
        # Questions and Anwsers
        if post.attrib.get("PostTypeId") != "1" and post.attrib.get("PostTypeId") != "2":
            continue

        user = users.get(post.attrib.get("OwnerUserId"))
        if user is None:
            user = post.attrib.get("OwnerDisplayName")
        if user is None:
            user = "Anonymous"

        # Post
        if post.attrib.get("ParentId") is None:
            tags = post.attrib.get("Tags")
            tags = tags[1:-1]
            tags = tags.split("><")

            document = {
                "title": post.attrib.get("Title"),
                "body": strip_tags(post.attrib.get("Body")),
                "body_type": "raw",
                "authors": [user],
                "id": "stackexchange-" + post.attrib.get("Id"),
                "tags": tags,
                "domain": "https://bitcoin.stackexchange.com",
                "url": "https://bitcoin.stackexchange.com/questions/" + post.attrib.get("Id"),
                "created_at": post.attrib.get("CreationDate"),
                "accepted_answer_id": post.attrib.get("AcceptedAnswerId"),
                "type": "question",
                "indexed_at": datetime.utcnow().isoformat()
            }
        else: # Answer
            # Fetch question from XML
            question = posts.get(post.attrib.get("ParentId"))
            if question is None:
                question = root.find("./row[@Id='" + post.attrib.get("ParentId") + "']")
                posts[post.attrib.get("ParentId")] = question

            document = {
                "body": strip_tags(post.attrib.get("Body")),
                "body_type": "raw",
                "authors": [user],
                "id": "stackexchange-" + post.attrib.get("Id"),
                "domain": "https://bitcoin.stackexchange.com",
                "url": "https://bitcoin.stackexchange.com/questions/" + post.attrib.get("ParentId") + "#" + post.attrib.get("Id"),
                "created_at": post.attrib.get("CreationDate"),
                "type": "answer",
                "title": question.attrib.get("Title") + " (Answer)",
                "indexed_at": datetime.utcnow().isoformat()
            }

        print("Adding document: " + document["id"], document["title"])
        documents.append(document)
        print("Uploading to vectorstore")
        upload_to_vectorstore(document)

    return documents

if __name__ == "__main__":
    if not os.path.exists(dir + "/bitcoin.stackexchange.com.7z"):
        download_dump()
    if not os.path.exists(dir + "/bitcoin.stackexchange.com"):
        extract_dump()

    # show status
    parse_users()
    docs = parse_posts()

    print ("Number of documents: " + str(len(docs)))
    print("Indexing documents...")

    i = 0
    while i < len(docs):
        success = False
        print("Indexing documents " + str(i) + " to " + str(i + 100))
        while not success:
            try:
                # Indexing documents to Elasticsearch
                bulk(
                    client=elastic_client(),
                    index=os.getenv("INDEX"),
                    actions=docs[i:i+100],
                    pipeline="avoid-duplicates"
                )
                success = True
            # handle elastic search connection error separately
            except Exception as e:
                import time
                print('Error: ' + str(e))
                print('Retrying in 10 seconds...')
                time.sleep(10)

        i += 100
