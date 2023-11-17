# Delvin Bitcoin To Elasticsearch

This project is mainly to push posts from [delvingbitcoin](https://delvingbitcoin.org/)'s forum to Elasticsearch.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Dependencies](#dependencies)

## Installation

1. Clone the GitHub repository:
   ```bash
   git clone https://github.com/MichealDavid1/repo-name.git
   cd repo-name
   ```

2. Install the required dependencies using [pip](https://pip.pypa.io/en/stable/):
   ```bash
   pip install -r requirements.txt
   ```

3. Or run the following command to set up the project:
   ```bash
   pip-compile --strip-extras requirements.in
   ```

## Usage

To run the script and upload posts to Elasticsearch, use the following command:

```bash
python delvingbitcoin_2_elasticsearch.py
```

Make sure to set up your Elasticsearch server. If you need help, refer to this [link](https://michealcodes.hashnode.dev/elasticsearch-with-python-on-macos-a-comprehensive-guide).

## Configuration

Edit the `.env` file to customize the configuration. You can modify the existing data or leave it as is.

## Dependencies

- Elasticsearch
- archive.py from Jamesob's [Github repo](https://github.com/jamesob/discourse-archive)
- All the functions needed for Elasticsearch operations are defined inside elastic.py file

---

**Note:** This README assumes familiarity with setting up Elasticsearch. If you are new to Elasticsearch, refer to [this link](https://opensource.com/article/19/7/installing-elasticsearch-macos) for installation instructions.
