# Usage

## Keep the folder in the scraper directory

```
scraper/general_scraper/
```

## ENV

Add the following values to the .env for scraper along with other environment variables.

```
SCRAPE_CONFIG_PATH=<path to json contining url and datapoints>
MODEL_CONFIG_PATH=<path to json containing model config>
```

SCRAPE_CONFIG_PATH: Format example
This json file is used to identify which URLs to scrape and what datapoints to extract from it. The json is a dict of
urls as keys, the values are a dict with "datapoints" key and list of datapoints as values. These datapoints are
injected into the prompt, so any specific directions/additions to the prompt can be added in this list.

```json
{
  "https://bitcointalk.org/index.php?topic=935898.0": {
    "datapoints": [
      "title",
      "author",
      "published/created date",
      "created_at",
      "topics"
    ]
  },
  "https://bitcoin.stackexchange.com/questions/122300/error-validating-transaction-transaction-orphaned-missing-reference-testnet": {
    "datapoints": [
      "title",
      "author",
      "published/created date",
      "created_at",
      "topics",
      "question",
      "question content",
      "answers",
      "answer votes",
      "comments",
      "user_statistics",
      ".Get full question content with all paragraphs."
    ]
  }
}
```

// Notice that any specific directions can be added to datapoints for a specific url

MODEL_CONFIG_PATH: Format example
Scrapegraph takes json configuration for llm model to be used. The supported models/services are mentioned in
scrapegraph repo and ones with known token counts are listed
at (https://github.com/ScrapeGraphAI/Scrapegraph-ai/blob/main/scrapegraphai/helpers/models_tokens.py).

The configuration requires "llm" key with model name. For script creation the "library" parameter is required. For some
graphs, an embedding model is also needed. Local installation of ollama (https://ollama.com/) is required if you want to
use local llm, but results are not that good.

1. Openai

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "model_provider": "openai",
    "temperature": 0.0
  },
  "embeddings": {
    "model": "gpt-4o-mini"
  },
  "library": "BeautifulSoup"
}
```

2. Ollama

```json
{
  "llm": {
    "model": "ollama/llama3.1",
    "model_provider": "ollama",
    "temperature": 0.0,
    "format": "json",
    "base_url": "http://localhost:11434"
  },
  "embeddings": {
    "model": "ollama/nomic-embed-text",
    "model_provider": "ollama",
    "base_url": "http://localhost:11434"
  },
  "library": "BeautifulSoup"
}
```

cd to folder and run main.py

```
cd general_scraper/
python3 main.py
```

# Workflow

Currently, the script needs to be run manually.
Set the environment variables (Elasticsearch, OpenAI and both config paths are necessary) and run main.py from the
directory. This will create another folder "generated_scripts" and cache scripts created by the llm for later use for
same domain/subdomain. If this is executed on cloud, a new way to cache these files might be needed (if caching is
required).

For all the sites to be scraped, create the SCRAPE_CONFIG_PATH json file with required urls and datapoints. The driver
code will sequentially scrape the given urls and save each in elasticsearch. The id is the url (the part after ://) and
special characters replaced by underscore followed by 5 characters of hash of datetime.datetme.now().