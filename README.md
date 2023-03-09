# Welcome to the scraper!

This scraper current runs on bitcoin stackexchange, the bitcoin optech repo, the bitcoin talk forum and bitcoin transcripts.

## Setup

You need an env file to indicate where you are pushing the data.

1. Copy `cp .env.sample .env`
2. run `cd common && yarn install && cd ../mailing-list && yarn install && cd ..`
3. To scrape a mailing list run `node mailing-list/main.js` with additional env vars like `URL='https://lists.linuxfoundation.org/pipermail/bitcoin-dev/'` and `NAME='bitcoin'`
3a. Or you can do something like `cd bitcoin.stackexchange.com && pip install -r requirements.txt && cd .. && python3 bitcoin.stackexchange.com/main.py`

You should be calling the scrapers from the root dir because they use the common dir.

## Other quirks

The bitcointalk forum scraper takes many hours to scrape so to start from the beginning, you'll need to do it from a server rather than use GitHub actions which has a 6 hours timeout. It's not a big deal if it times out on GitHub actions because it's written to index the last 100 posts and work in reverse chronological order.

## These scrapers pull EVERYTHING

If testing on your local machine, it won't pull things it already has, but it will for GitHub actions. This could be optimized.
