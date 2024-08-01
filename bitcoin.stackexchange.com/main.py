import os
import sys
import traceback
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger
from tqdm import tqdm

from utils import download_dump, extract_dump, parse_posts, parse_users, strip_tags

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.scraper_log_utils import scraper_log_csv
from common.elasticsearch_utils import upsert_document

if __name__ == "__main__":
    inserted_ids = set()
    updated_ids = set()
    no_changes_ids = set()
    error_occurred = False
    error_message = "---"

    try:
        INDEX = os.getenv("INDEX")

        BASE_DIR = os.getenv("DATA_DIR", ".")
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

                try:
                    res = upsert_document(index_name=os.getenv('INDEX'), doc_id=document['id'], doc_body=document)
                    if res['result'] == 'created':
                        inserted_ids.add(res['_id'])
                    elif res['result'] == 'updated':
                        updated_ids.add(res['_id'])
                    elif res['result'] == 'noop':
                        no_changes_ids.add(res['_id'])
                except Exception as e:
                    # error_occurred = True
                    logger.error(f"Error upserting document ID-{document['id']}: {e}")
                    logger.warning(document)

            except Exception as ex:
                # error_occurred = True
                error_log = f"{ex}\n{traceback.format_exc()}"
                logger.error(error_log)
                logger.warning(post)

        logger.info(f"All Documents updated successfully!")

    except Exception as main_e:
        error_message = f"error: {main_e}\n{traceback.format_exc()}"

    finally:
        scraper_log_csv(f"bitcoin_stackexchange.csv", scraper_domain="https://bitcoin.stackexchange.com",
                        inserted_docs=len(inserted_ids),
                        updated_docs=len(updated_ids), no_changes_docs=len(no_changes_ids), error=error_message)
