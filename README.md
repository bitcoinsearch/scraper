# Welcome to the scraper!

This scraper current runs on bitcoin stackexchange, the bitcoin optech repo, the bitcoin talk forum and bitcoin transcripts.

## Setup

You need an env file to indicate where you are pushing the data.

1. Copy `cp .env.sample .env`
2. run `cd common && yarn install && cd ../mailing-list && yarn install && cd ..`
3. To scrape a mailing list run `node mailing-list/main.js` with additional env vars like `URL='https://lists.linuxfoundation.org/pipermail/bitcoin-dev/'` and `NAME='bitcoin'`
3a. Or you can do something like `cd bitcoin.stackexchange.com && pip install -r requirements.txt && cd .. && python3 bitcoin.stackexchange.com/main.py`

You should be calling the scrapers from the root dir because they use the common dir.

## Scrapybot 

This section explains how to run the scrapers in `scrapybot` folder

The folder has a bunch of crawlers(spiders) in the `scrapybot/scrapybot/spiders` folder. Each of the crawler files is specific to a particular site.
To run a crawler using scrapybot, for example `rusty`, which will scrape the site `https://rusty.ozlabs.org`,switch to the root directory(where there is this README file) and run these commands from your terminal:
- `pip install -r requirements.txt && cd scrapybot`
- ` scrapy crawl rusty -O rusty.json`

The above commands will install scrapy dependencies, then run the `rusty` spider(one of the crawlers) and store the collected document in `rusty.json` file in the `scrapybot` project directory

The same procedure can be applied to any of the crawlers in the `scrapybot/spiders` directory. There is also a script in `Scrapybot` directory called `scraper.sh` which can run all the spiders at once


### Sending the output to elastic search

- create an `example.ini` file inside the `scrapybot` directory with the following contents
```
[ELASTIC]
cloud_id = `your_cloud_id` 
user = `your_elasticsearch_username`
password =  `your_elasticsearch_password`
```
- inside the `pipelines.py file` in the `scrapybot` directory, read the above file to load your elasticsearch credentials with the line below:
```
config.read("/path/to/your/example.ini") - replace what's in quotes with your actual `ini` file
```

## Other quirks

The bitcointalk forum scraper takes many hours to scrape so to start from the beginning, you'll need to do it from a server rather than use GitHub actions which has a 6 hours timeout. It's not a big deal if it times out on GitHub actions because it's written to index the last 100 posts and work in reverse chronological order.

## These scrapers pull EVERYTHING

If testing on your local machine, it won't pull things it already has, but it will for GitHub actions. This could be optimized.
