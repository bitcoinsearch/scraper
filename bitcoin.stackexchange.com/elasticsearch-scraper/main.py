import requests
import os
from dotenv import load_dotenv
from util import app_search, strip_tags, elastic_client
from elasticsearch.helpers import bulk
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
                "type": "question"
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
            }

        print("Adding document: " + document["id"], document["title"])
        documents.append(document)

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
                    actions=docs[i:i+100]
                )
                success = True
            except:
                import time
                time.sleep(10)
                pass
    
        i += 100
