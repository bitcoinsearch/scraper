# Welcome to the scraper!

This project is designed to automate the process of gathering information from a variety of key Bitcoin-related sources.
It leverages GitHub Actions to schedule nightly cron jobs, ensuring that the most up-to-date content is captured from each source according to a defined frequency.
The scraped data are then stored in an Elasticsearch index.

Below is a detailed breakdown of the sources scraped and the schedule for each:

Daily at 00:00 AM UTC

- [Lightning Mailing List](https://lists.linuxfoundation.org/pipermail/lightning-dev/) ([cron](.github/workflows/mailing-list-lightning.yml), [source](mailing-list))
- [New Bitcoin Mailing List](https://gnusha.org/pi/bitcoindev/) ([cron](.github/workflows/mailing-list-bitcoin-new.yml), [source](mailing-list/main.py))
- [Bitcoin Mailing List](https://lists.linuxfoundation.org/pipermail/bitcoin-dev/) ([cron](.github/workflows/mailing-list-bitcoin.yml), [source](mailing-list))
- [Delving Bitcoin](https://delvingbitcoin.org/) ([cron](.github/workflows/delving-bitcoin.yml), [source](delvingbitcoin_2_elasticsearch))

Weekly

- [bitcoin.stackexchange](https://bitcoin.stackexchange.com/) ([cron](.github/workflows/stackexchange.yml), [source](bitcoin.stackexchange.com))
- Bitcoin Talk Forum ([cron](.github/workflows/bitcointalk.yml), [source](bitcointalk))
  - only the [Development & Technical Discussion Board](https://bitcointalk.org/index.php?board=6.0)
  - only for specific authors
- [Bitcoin Transcript](https://btctranscripts.com/) ([cron](.github/workflows/bitcointranscripts.yml), [source](bitcointranscripts))
- [Bitcoin Optech](https://bitcoinops.org/) ([cron](.github/workflows/bitcoinops.yml), [source](bitcoinops))

Additionally, for on-demand scraping tasks, we utilize a Scrapybot, details of which can be found in the [Scrapybot section](#scrapybot) below.

## Setup

You need an env file to indicate where you are pushing the data.

1. Copy `cp .env.sample .env`
2. If you want to run Elastic Search locally, update the `ES_LOCAL_URL = ` with your local elastic search url
3. run `cd common && yarn install && cd ../mailing-list && yarn install && cd ..`
4. To scrape a mailing list run `node mailing-list/main.js` with additional env vars like `URL='https://lists.linuxfoundation.org/pipermail/bitcoin-dev/'` and `NAME='bitcoin'`
   3a. Or you can do something like `cd bitcointranscripts && pip install -r requirements.txt && cd .. && python3 bitcointranscripts/main.py

You should be calling the scrapers from the root dir because they use the common dir.

## Scrapybot

We have implemented a variety of crawlers (spiders), each designed for a specific website of interest.
You can find all the spiders in the [`scrapybot/scrapybot/spiders`](scrapybot/scrapybot/spiders) directory.

This section explains how to run the scrapers in the `scrapybot` folder.

To run a crawler using scrapybot, for example `rusty`, which will scrape the site `https://rusty.ozlabs.org`, switch to the root directory(where there is this README file) and run these commands from your terminal:

- `pip install -r requirements.txt && cd scrapybot`
- `scrapy crawl rusty -O rusty.json`

The above commands will install scrapy dependencies, then run the `rusty` spider(one of the crawlers) and store the collected document in `rusty.json` file in the `scrapybot` project directory.

The same procedure can be applied to any of the crawlers in the `scrapybot/spiders` directory.
There is also a script in `scrapybot` directory called `scraper.sh` which can run all the spiders at once.

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
