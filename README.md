# Welcome to the scraper!

This scraper currently runs on bitcoin stackexchange, the bitcoin optech repo, the bitcoin talk forum, bitcoin transcripts, delving bitcoin, bitcoin protocol discussion lists (bitcoin-dev) and development discussion of the Lightning Network Bitcoin Caching Layer (lightning-dev).

## Overview

This repository contains a robust solution for scraping Bitcoin-related articles from various sources and storing them efficiently in an ElasticSearch index. With the growing interest in cryptocurrencies like Bitcoin, having a tool to aggregate and analyze news articles can be invaluable for staying updated and making informed decisions.

## Key Features:

1. Scraping Multiple Sources: Utilizes web scraping techniques to gather Bitcoin-related articles from diverse sources.
2. Data Parsing: Parses the scraped content to extract relevant information such as article title, author, publication date, content, and any associated metadata.
3. ElasticSearch Integration: Seamlessly indexes the parsed article data into ElasticSearch, facilitating fast and flexible search queries and data analysis.
4. Data Normalization: Standardizes the format of the scraped data to ensure consistency and ease of retrieval during search operations.
5. Scheduled Execution: Supports scheduled execution of the scraping and indexing process to keep the ElasticSearch index up-to-date with the latest Bitcoin-related articles.

## Cron jobs

1. BitCoin Optech: [Data Source](https://github.com/bitcoinops/bitcoinops.github.io/archive/refs/heads/) -- [Cron Job Source](https://github.com/bitcoinsearch/scraper/blob/master/.github/workflows/bitcoinops.yml)
    - **Schedule**: Every Wednesday at 1pm UTC
    - The purpose of this cron job is to automate the process of fetching data from BitCoin Optech and indexing it into ElasticSearch. By running this job on a weekly basis, every Wednesday at 1pm UTC, users can ensure that their ElasticSearch index remains up-to-date with the latest information from BitCoin Optech.
2. BitCoin Talk: [Data Source](https://bitcointalk.org/index.php?board=6) -- [Cron Job Source](https://github.com/bitcoinsearch/scraper/blob/master/.github/workflows/bitcointalk.yml)
    - **schedule**: Every Wednesday at 1pm UTC
    - This cron job is designed to fetch articles and topics from the BitCoin Talk website and store them in an ElasticSearch index. BitCoin Talk is a popular forum for discussions related to Bitcoin, making this cron job valuable for aggregating community insights and discussions into a searchable index.
    - The purpose of this cron job is to automate the process of fetching articles and topics from BitCoin Talk and indexing them into ElasticSearch. By running this job regularly, users can ensure that their ElasticSearch index remains updated with the latest discussions and insights from the BitCoin Talk community.
3. BitCoin Transcript : [Data Source](https://github.com/bitcointranscripts/bitcointranscripts) -- [Cron Job Source](https://github.com/bitcoinsearch/scraper/blob/master/.github/workflows/bitcointranscripts.yml)
    - **schedule**: Every Wednesday at 1pm UTC
    - This cron job is designed to fetch data from the BitcoinTranscript GitHub repository archives. BitcoinTranscript is a valuable resource that archives transcripts of discussions, presentations, and meetings related to Bitcoin, making this cron job essential for those interested in historical insights and developments within the Bitcoin community.
    - The purpose of this cron job is to automate the process of fetching data from the BitcoinTranscript GitHub repository archives and possibly storing it for analysis or archival purposes. By running this job every Wednesday at 1 PM UTC, users can ensure that they regularly access and preserve the valuable content available in the BitcoinTranscript archives.
4. Delving BitCoin  : [Data Source](https://delvingbitcoin.org) -- [Cron Job Source](https://github.com/bitcoinsearch/scraper/blob/master/.github/workflows/delving-bitcoin.yml)
    - **schedule**: Every Wednesday at 1pm UTC
    - This Python-based cron job is designed to fetch data from the Delving Bitcoin website and store it in an ElasticSearch index. Delving Bitcoin is a valuable resource for exploring and understanding various aspects of Bitcoin, making this cron job essential for those interested in in-depth analysis and research within the Bitcoin ecosystem.
    - The purpose of this cron job is to automate the process of fetching data from the Delving Bitcoin website and indexing it into ElasticSearch. By running this job on a regular basis, users can ensure that their ElasticSearch index remains updated with the latest insights, research papers, and data available on Delving Bitcoin.
5. New Bitcoin Mailing list  : [Data Source](https://gnusha.org/pi/bitcoindev/) -- [Cron Job Source](https://github.com/bitcoinsearch/scraper/blob/master/.github/workflows/mailing-list-bitcoin-new.yml)
    - **schedule**: Every Day at 00:00 (Mid Night)
    - This Python-based cron job is designed to fetch data, threads, and replies from the BitcoinDev website's mailing list and store it in an ElasticSearch index. The BitcoinDev mailing list is a crucial platform for discussions, proposals, and development updates related to Bitcoin, making this cron job indispensable for those interested in staying informed about the latest developments in Bitcoin development.
6. Bitcoin Mailing list: [Data Source](https://lists.linuxfoundation.org/pipermail/) -- [Cron Job Source](https://github.com/bitcoinsearch/scraper/blob/master/.github/workflows/mailing-list-bitcoin.yml)
    - **schedule**: Every Day at 00:00 (Mid Night)
    - The purpose of this cron job is to automate the process of fetching data from the Bitcoin mailing list and indexing it into ElasticSearch. By running this job daily at midnight, users can ensure that their ElasticSearch index remains up-to-date with the latest discussions and announcements from the Bitcoin community.

7. Lightning Mailing list: [Data Source](https://lists.linuxfoundation.org/pipermail/lightning-dev/) -- [Cron Job Source](https://github.com/bitcoinsearch/scraper/blob/master/.github/workflows/mailing-list-lighting.yml)
    -  **schedule**: Every Day at 00:00 (Mid Night)
    - This cron job is designed to fetch posts and discussions from the Lightning Development mailing list hosted at https://lists.linuxfoundation.org/pipermail/lightning-dev/ and store them in an ElasticSearch index. The Lightning Development mailing list serves as a crucial platform for discussions and development updates related to the Lightning Network, a caching layer for Bitcoin, making this cron job essential for staying informed about the latest developments in Lightning Network technology.
    - The purpose of this cron job is to automate the process of fetching posts and discussions from the Lightning Development mailing list and indexing them into ElasticSearch. By running this job regularly, users can ensure that their ElasticSearch index remains updated with the latest discussions, proposals, and development updates from the Lightning Network community.
8. StackExchange : [Data Source](https://lists.linuxfoundation.org/pipermail/lightning-dev/) -- [Cron Job Source](https://github.com/bitcoinsearch/scraper/blob/master/.github/workflows/stackexchange.yml)
    -  **schedule**: Every Sunday at 00:00 (Mid Night)
    - This Python-based cron job is designed to fetch discussions related to Bitcoin from the StackExchange platform and store them in an ElasticSearch index. StackExchange is a popular platform for asking questions, sharing knowledge, and engaging in discussions on various topics, including Bitcoin, making this cron job essential for aggregating and indexing valuable insights from the Bitcoin community.
    - The purpose of this cron job is to automate the process of fetching Bitcoin-related discussions from StackExchange and indexing them into ElasticSearch. By running this job every Sunday at midnight, users can ensure that their ElasticSearch index remains updated with the latest discussions and insights from the StackExchange Bitcoin community.


## Setup

You need an env file to indicate where you are pushing the data.

1. Copy `cp .env.sample .env`
2. run `cd common && yarn install && cd ../mailing-list && yarn install && cd ..`
3.
    - To scrape a mailing list run `node mailing-list/main.js` with additional env vars like `URL='https://lists.linuxfoundation.org/pipermail/bitcoin-dev/'` and `NAME='bitcoin'` 
    ---
    
    - you can do something like `cd bitcoin.stackexchange.com && pip install -r requirements.txt && cd .. && python3 bitcoin.stackexchange.com/main.py`

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
