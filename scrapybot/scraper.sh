#!/bin/bash

spiders=("bolts" "btcphilosophy" "grokkingbtc" "learnmeabitcoin" "lndocs" "oleganza" "programmingbtc" "river" "rusty" "bips" "bitmex" "blips" "andreasbooks")

for spider in "${spiders[@]}"
do
  echo "Running spider: $spider"
  scrapy crawl "$spider" --nolog
  sleep 5
  echo "Sleeping for 5 seconds..."
done

