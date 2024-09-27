#!/bin/bash

# Define the spiders to be run from below commented ones
# "bolts" "btcphilosophy" "grokkingbtc" "learnmeabitcoin" "lndocs" "oleganza" "programmingbtc" "river" "rusty"  "andreasbooks"
spiders=("blips" "bips")

# Change to the directory where Scrapy spiders are located
cd "scrapybot/scrapybot/spiders" || { echo "Directory not found!"; exit 1; }

# Loop through the spiders and run them one by one
for spider in "${spiders[@]}"
do
  echo "Running spider: $spider"
  scrapy crawl "$spider" --nolog
  echo "Sleeping for 5 seconds..."
  sleep 5
done

