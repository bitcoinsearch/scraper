import os
import time
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
from tqdm import tqdm
from utils import download_dump, extract_dump, parse_posts, parse_users, strip_tags, find_and_delete_document_by_source_id, es, document_view, document_add
import traceback
load_dotenv()


if __name__ == "__main__":

    INDEX = os.getenv("INDEX")

    BASE_DIR = os.getenv("DATA_DIR", ".")
    DOWNLOAD_PATH = os.path.join(BASE_DIR, "bitcoin.stackexchange.com.7z")
    EXTRACT_PATH = os.path.join(BASE_DIR, "bitcoin.stackexchange.com")

    # download archive data
    if not os.path.exists(DOWNLOAD_PATH):
        download_dump(DOWNLOAD_PATH)
    else:
        logger.info(f'File already exists at path: {os.path.abspath(DOWNLOAD_PATH)}')

    # extract the data
    if not os.path.exists(EXTRACT_PATH):
        extract_dump(DOWNLOAD_PATH, EXTRACT_PATH)
    else:
        logger.info(f'{len(os.listdir(EXTRACT_PATH))}, files already exists at path: {os.path.abspath(EXTRACT_PATH)}')

    # parse the data
    USERS_FILE_PATH = f"{EXTRACT_PATH}/Users.xml"
    users = parse_users(USERS_FILE_PATH)

    POSTS_FILE_PATH = f"{EXTRACT_PATH}/Posts.xml"
    docs = parse_posts(POSTS_FILE_PATH)

    for post in tqdm(docs):
        try:
            if post.attrib.get("PostTypeId") != "1" and post.attrib.get("PostTypeId") != "2":
                continue

            user = users.get(post.attrib.get("OwnerUserId")) or post.attrib.get("OwnerDisplayName") or "Anonymous"

            # prepare the document based on type: 'question' or 'answer'
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
                    "thread_url": "https://bitcoin.stackexchange.com/questions/" + post.attrib.get("Id"),
                    "created_at": post.attrib.get("CreationDate"),
                    "accepted_answer_id": post.attrib.get("AcceptedAnswerId"),
                    "type": "question",
                    "indexed_at": datetime.utcnow().isoformat()
                }
            else:
                posts = {}
                question = posts.get(post.attrib.get("ParentId"))
                if question is None:
                    question = docs.find("./row[@Id='" + post.attrib.get("ParentId") + "']")
                    posts[post.attrib.get("ParentId")] = question

                document = {
                    "title": question.attrib.get("Title") + " (Answer)",
                    "body": strip_tags(post.attrib.get("Body")),
                    "body_type": "raw",
                    "authors": [user],
                    "id": "stackexchange-" + post.attrib.get("Id"),
                    "domain": "https://bitcoin.stackexchange.com",
                    "url": "https://bitcoin.stackexchange.com/questions/" + post.attrib.get(
                        "ParentId") + "#" + post.attrib.get("Id"),
                    "thread_url": "https://bitcoin.stackexchange.com/questions/" + post.attrib.get(
                        "ParentId") + "#" + post.attrib.get("Id"),
                    "created_at": post.attrib.get("CreationDate"),
                    "type": "answer",
                    "indexed_at": datetime.utcnow().isoformat()
                }

            # delete posts with previous logic where '_id' was set on its own
            this_id = document['id']
            logger.warning(f"this_id: {this_id}")
            _ = find_and_delete_document_by_source_id(es, INDEX, this_id)

            # insert the doc if it doesn't exist, with '_id' set by our logic
            resp = document_view(index_name=INDEX, doc_id=document['id'])
            if not resp:
                _ = document_add(index_name=INDEX, doc=document, doc_id=document['id'])
                logger.success(f"Added! ID: {document['id']}, Title: {document['title']}")
            else:
                logger.info(f"Exist! ID: {document['id']}, Title: {document['title']}")

        except Exception as ex:
            logger.error(f"Error occurred: {ex} \n{traceback.format_exc()}")
            time.sleep(5)

    logger.info(f"All Documents updated successfully!")
