#!/usr/bin/env python3
"""
This script does a basic archive of Discourse content by way of its API.
"""
import argparse
import urllib.request
import sys
import time
import os
import json
import functools
import datetime
from dataclasses import dataclass
from pathlib import Path
from dateutil.parser import parse
from loguru import logger as log

# import logging
# loglevel = 'DEBUG' if os.environ.get('DEBUG') else 'INFO'
# try:
#     # If `rich` is installed, use pretty logging.
#     from rich.logging import RichHandler
#     logging.basicConfig(level=loglevel, datefmt="[%X]", handlers=[RichHandler()])
# except ImportError:
#     logging.basicConfig(level=loglevel)

# log = logging.getLogger('archive')


parser = argparse.ArgumentParser(
    'discourse-archive',
    description='Create a basic content archive from a Discourse installation')
parser.add_argument(
    '-u', '--url', help='URL of the Discourse server',
    default=os.environ.get('DISCOURSE_URL', 'https://delvingbitcoin.org'))
parser.add_argument(
    '--debug', action='store_true', default=os.environ.get('DEBUG'))
parser.add_argument(
    '-t', '--target-dir', help='Target directory for the archive',
    default=Path(os.environ.get('TARGET_DIR', './archive')))


@functools.cache
def args():
    return parser.parse_args()


def http_get(path) -> str:
    log.debug(f"HTTP GET {path}")
    backoff = 3

    while True:
        try:
            with urllib.request.urlopen(f"{args().url}{path}") as f:
                return f.read().decode()
        except Exception:
            time.sleep(backoff)
            backoff *= 2

            if backoff >= 256:
                log.exception('ratelimit exceeded, or something else wrong?')
                sys.exit(1)


def http_get_json(path) -> dict:
    try:
        return json.loads(http_get(path))
    except json.JSONDecodeError:
        log.warning(f"unable to decode JSON response from {path}")
        raise


class PostSlug:
    @classmethod
    def id_from_filename(cls, name: str) -> int:
        return int(name.split('-', 1)[0])


@dataclass(frozen=True)
class PostTopic:
    id: int
    slug: str
    title: str


@dataclass(frozen=True)
class Post:
    id: int
    slug: str
    raw: dict

    def get_created_at(self) -> datetime.datetime:
        # return datetime.datetime.fromisoformat(parse(self.raw['created_at']))
        return parse(self.raw['created_at'])

    def save(self, dir: Path):
        """Write the raw post to disk."""
        idstr = str(self.id).zfill(10)
        filename = f"{idstr}-{self.raw['username']}-{self.raw['topic_slug']}.json"
        folder_name = self.get_created_at().strftime('%Y-%m-%B')
        full_path = dir / folder_name / filename
        full_path.parent.mkdir(parents=True, exist_ok=True)
        log.info(f"saving post {self.id} to {full_path}")
        full_path.write_text(json.dumps(self.raw, indent=2))

    def get_topic(self) -> PostTopic:
        return PostTopic(
            id=self.raw['topic_id'],
            slug=self.raw['topic_slug'],
            title=self.raw['topic_title'],
        )

    @classmethod
    def from_json(cls, j: dict) -> 'Post':
        return cls(
            id=j['id'],
            slug=j['topic_slug'],
            raw=j,
        )


@dataclass(frozen=True)
class Topic:
    id: int
    slug: str
    raw: dict
    markdown: str

    def get_created_at(self) -> datetime.datetime:
        return parse(self.raw['created_at'])

    def save_rendered(self, dir: Path):
        """Write the rendered (.md) topic to disk."""
        date = str(self.get_created_at().date())
        filename = f"{date}-{self.slug}-id{self.id}.md"
        folder_name = self.get_created_at().strftime('%Y-%m-%B')
        full_path = dir / folder_name / filename
        full_path.parent.mkdir(parents=True, exist_ok=True)
        log.info(f"saving topic markdown {self.id} to {full_path}")
        markdown = f"# {self.raw['title']}\n\n{self.markdown}"
        full_path.write_text(markdown)

    def get_topic(self) -> PostTopic:
        return PostTopic(
            id=self.raw['topic_id'],
            slug=self.raw['topic_slug'],
            title=self.raw['topic_title'],
        )

    @classmethod
    def from_json(cls, t: dict, markdown: str) -> 'Topic':
        return cls(
            id=t['id'],
            slug=t['slug'],
            raw=t,
            markdown=markdown,
        )


def download_dumps() -> None:
    """
    Sync posts back to `metdata[last_sync_date] - 1 day`, and then save the rendered
    version of all topics associated with those posts.
    """
    target_dir = args().target_dir
    target_dir = Path(target_dir) if not isinstance(target_dir, Path) else target_dir

    (posts_dir := target_dir / 'posts').mkdir(parents=True, exist_ok=True)
    (topics_dir := target_dir / 'rendered-topics').mkdir(parents=True, exist_ok=True)

    metadata_file = target_dir / '.metadata.json'
    last_sync_date = None
    metadata = {}

    if metadata_file.exists():
        metadata = json.loads(metadata_file.read_text())
        last_sync_date = parse(metadata['last_sync_date'])

    if last_sync_date:
        # Resync over the last day to catch any post edits.
        last_sync_date -= datetime.timedelta(days=1)

    log.info("detected latest synced post date:{last_sync_date}")

    topics_to_get = {}
    max_created_at = None
    last_created_at: datetime.datetime | None = None
    last_id: int | None = None

    posts = http_get_json('/posts.json')['latest_posts']
    no_new_posts = False

    while posts:
        log.info(f"processing {len(posts)} posts")
        for json_post in posts:
            try:
                post = Post.from_json(json_post)
            except Exception:
                log.warning(f"failed to deserialize post {json_post}")
                raise
            last_created_at = post.get_created_at()

            if last_sync_date is not None:
                no_new_posts = last_created_at < last_sync_date
                if no_new_posts:
                    break

            post.save(posts_dir)

            if not max_created_at:
                # Set in this way because the first /post.json result returned will be
                # the latest created_at.
                max_created_at = post.get_created_at()

            last_id = post.id
            topic = post.get_topic()
            topics_to_get[topic.id] = topic

        if no_new_posts or last_id is not None and last_id <= 1:
            log.info("no new posts, stopping")
            break

        time.sleep(5)
        posts = http_get_json(
            f'/posts.json?before={last_id - 1}')['latest_posts']

        # Discourse implicitly limits the posts query for IDs between `before` and
        # `before - 50`, so if we don't get any results we have to kind of scan.
        while not posts and last_id >= 0:
            # This is probably off-by-one, but doesn't hurt to be safe.
            last_id -= 49
            posts = http_get_json(
                f'/posts.json?before={last_id}')['latest_posts']
            time.sleep(1)

    if max_created_at is not None:
        metadata['last_sync_date'] = max_created_at.isoformat()
        log.info(f"writing metadata: {metadata}")
        metadata_file.write_text(json.dumps(metadata, indent=2))

    time.sleep(3)

    for topic in topics_to_get.values():
        try:            
            data = http_get_json(f"/t/{topic.id}.json")
            body = http_get(f"/raw/{topic.id}")
            page_num = 2

            if not body:
                log.warning(f"could not retrieve topic {topic.id} markdown")
                continue

            while more_body := http_get(f"/raw/{topic.id}?page={page_num}"):
                body += f"\n{more_body}"

            t = Topic.from_json(data, body)
            t.save_rendered(topics_dir)
            log.info(f"saved topic {t.id} ({t.slug})")

            time.sleep(0.3)
        except:
            pass

    return no_new_posts
    

if __name__ == "__main__":
    _ = download_dumps()