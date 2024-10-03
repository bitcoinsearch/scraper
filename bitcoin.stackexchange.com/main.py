import os
import sys
import time
from datetime import datetime
from loguru import logger
from tqdm import tqdm

from utils import download_dump, extract_dump, parse_posts, parse_users, strip_tags, document_view, document_add
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conf import INDEX_NAME, DATA_DIR

if __name__ == "__main__":
    BASE_DIR = os.getenv(DATA_DIR, ".")
    DOWNLOAD_PATH = os.path.join(BASE_DIR, "bitcoin.stackexchange.com.7z")
    EXTRACT_PATH = os.path.join(BASE_DIR, "bitcoin.stackexchange.com")

    # download archive data
    if not os.path.exists(DOWNLOAD_PATH):
        download_dump(DOWNLOAD_PATH)
    else:
        logger.info(f'File already exists at path: {os.path.abspath(DOWNLOAD_PATH)}')

    # extract the data if necessary
    if not os.path.exists(EXTRACT_PATH):
        os.makedirs(EXTRACT_PATH)
        should_extract = True
    else:
        if not os.listdir(EXTRACT_PATH):
            should_extract = True
        else:
            file_count = len(os.listdir(EXTRACT_PATH))
            logger.info(f'{file_count} files already exist at path: {os.path.abspath(EXTRACT_PATH)}')
            should_extract = False

    if should_extract:
        extract_dump(DOWNLOAD_PATH, EXTRACT_PATH)

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

            # # delete posts with previous logic where '_id' was set on its own and replace them with our logic
            # this_id = document['id']
            # logger.info(f"this_id: {this_id}")
            # _ = find_and_delete_document_by_source_id(INDEX, this_id)

            # insert the doc if it doesn't exist, with '_id' set by our logic
            resp = document_view(index_name=INDEX_NAME, doc_id=document['id'])
            if not resp:
                _ = document_add(index_name=INDEX_NAME, doc=document, doc_id=document['id'])
                logger.success(f"Added! ID: {document['id']}, Title: {document['title']}")
            else:
                # logger.info(f"Exist! ID: {document['id']}, Title: {document['title']}")
                pass

        except Exception as ex:
            logger.error(f"Error occurred: {ex} \n{traceback.format_exc()}")
            time.sleep(5)

    logger.info(f"All Documents updated successfully!")
