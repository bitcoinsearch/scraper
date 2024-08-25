# Usage

## Keep the folder in the scraper directory
```
scraper/general_scraper/
```

## ENV
Add the following values to the .env
```
SCRAPE_CONFIG_PATH=<path to json contining url and datapoints>
MODEL_CONFIG_PATH=<path to json containing model config>
```

SCRAPE_CONFIG_PATH: Format example
```json
{
    "https://bitcointalk.org/index.php?topic=935898.0": {
        "datapoints": [
            "title", "author", "published/created date", "created_at",
            "topics"
        ]
    },
    "https://bitcoin.stackexchange.com/questions/122300/error-validating-transaction-transaction-orphaned-missing-reference-testnet": {
        "datapoints": [
            "title", "author", "published/created date", "created_at",
            "topics", "question", "question content", "answers", "answer votes", "comments",
                "user_statistics", ".Get full question content with all paragraphs."
        ]
    }
}
```
// Notice that any specific directions can be added to datapoints for a specific url

MODEL_CONFIG_PATH: Format example
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


## Current issues:
The approach uses a script creator and an llm answer generator. Script creator performs better for data across multile ags, like stackexchange question/answers but does not perform chunking at the moment, hence, it'll throw error for large htmls