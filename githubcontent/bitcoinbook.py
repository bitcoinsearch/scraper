import json
from utils import GithubScraper

scraper = GithubScraper()

def get_bitcoinbook_data():

    chapters = []
    for i in range(1,13):
        number = '0' + str(i) if i < 10 else str(i)
        chapters.append(number)

    base_url = 'https://github.com/bitcoinbook/bitcoinbook/blob/develop/ch{}.asciidoc'
    print("Getting links for bitcoin book")
    chapter_links = scraper.get_github_urls(base_url,chapters)
    bitcoindocs = scraper.parse_aantonop_books(chapter_links)
    print("Number of documents: " + str(len(bitcoindocs)))

    with open("bitcoinbook.json", "w") as f:
      json.dump(bitcoindocs, f, indent=4)
    # Close the file
    f.close()


if __name__ == "__main__":

    get_bitcoinbook_data()
