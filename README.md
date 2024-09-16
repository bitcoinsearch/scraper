# Welcome to the Scraper

This project is designed to automate the process of gathering information from a variety of key Bitcoin-related sources.
It leverages GitHub Actions to schedule nightly cron jobs, ensuring that the most up-to-date content is captured from
each source according to a defined frequency.
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

## Prerequisites

Before you begin, ensure you have following installed:

- [Python 3.8+](https://www.python.org/downloads/)
- [Node.js 14+](https://nodejs.org/)
- [pip](https://pip.pypa.io/en/stable/)
- [yarn](https://classic.yarnpkg.com/en/docs/install/)
- [Elasticsearch](https://www.elastic.co/downloads/elasticsearch)
- [virtualenv](https://virtualenv.pypa.io/en/latest/)

## Setup Instructions

1. **Clone this repository**
    ```bash
    https://github.com/bitcoinsearch/scraper.git
   cd bitcoin-scrapers
   ```

2. **Create a virtual environment**
    ```bash
   python -m venv venv
   ```
3. **Activate the virtual environment**
    - **Windows:**
      ```bash
      venv\Scripts\activate
      ```
    - **MacOS/Linux:**
      ```bash
      source venv/bin/activate
      ```
4. **Install the required Python packages**
    ```bash
   pip install -r requirements.txt
   ```
5. **Create .env file from env.sample file**
    ```bash
    cp .env.sample .env
    ```
   Open the .env file and provide the necessary values for the following variables:
    - `DATA_DIR`: Path to store temporary files.
    - `DAYS_TO_SUBTRACT`: Number of days to subtract from today's date to determine the date range for scraping and downloading documents for mailing list.
    - `URL`: For mailing list scraper, use one of these URLs:
       1. https://lists.linuxfoundation.org/pipermail/lightning-dev/
       2. https://lists.linuxfoundation.org/pipermail/bitcoin-dev/  
    - `CLOUD_ID`: Your Elasticsearch cloud ID. This is required for connecting to your Elasticsearch cluster.
    - `USERNAME`: The username for your Elasticsearch instance.
    - `USER_PASSWORD`: The API key or password associated with the `USERNAME` in Elasticsearch.
    - `INDEX`: The name of the index where documents will be stored in Elasticsearch.


6. **Node.js Packages/Dependencies installation**

   Run below command to install required packages for node.js scrapers.
   ```bash
   cd common && yarn install && cd ../mailing-list && yarn install && cd ..   
   ```


## Running Scrapers
   To run a specific scraper, use the respective command listed below:
1. [bitcoin.stackexchange.com](bitcoin.stackexchange.com)
   ```bash
   python .\bitcoin.stackexchange.com\main.py
   ```
2. [bitcoinbook](bitcoinbook)
   ```bash
   python .\bitcoinbook\main.py
   ```
3. [bitcoinops](bitcoinops)
   ```bash
   python .\bitcoinops\main.py
   ```
4. [bitcointalk](bitcointalk)
   ```bash
   python .\bitcointalk\main.py
   ```
5. [bitcointranscripts](bitcointranscripts)
   ```bash
   python .\bitcointranscripts\main.py
   ```
6. [delvingbitcoin_2_elasticsearch](delvingbitcoin_2_elasticsearch)
   ```bash
   python .\delvingbitcoin_2_elasticsearch\delvingbitcoin_2_elasticsearch.py
   ```
7. [mailing-list](mailing-list)


   - To run the mailing list scrapers, use the following commands based on the type of documents you want to scrape:
     - **For Linux Foundation Documents**
       
         Ensure that the `URL` environment variable is set to the appropriate mailing list URL (e.g., `https://lists.linuxfoundation.org/pipermail/lightning-dev/` or `https://lists.linuxfoundation.org/pipermail/bitcoin-dev/`). 
         Run the following command:
         ```bash
        node mailing-list/main.js
         ``` 
     - **For New Bitcoin Dev** 
        Use the following command to run the Bitcoin Dev scraper:
        ```bash
        python .\mailing-list\main.py
        ```


## Other quirks

The bitcointalk forum scraper takes many hours to scrape so to start from the beginning, you'll need to do it from a server rather than use GitHub actions which has a 6 hours timeout. It's not a big deal if it times out on GitHub actions because it's written to index the last 100 posts and work in reverse chronological order.

## These scrapers pull EVERYTHING

If testing on your local machine, it won't pull things it already has, but it will for GitHub actions. This could be optimized.
