import json
from utils import GithubScraper

scraper = GithubScraper()

def get_lightningbook_data():
    chapters = ['01_introduction','02_getting_started','03_how_ln_works','04_node_client',
                '05_node_operations','06_lightning_architecture','07_payment_channels','08_routing_htlcs',
                '09_channel_operation','10_onion_routing','11_gossip_channel_graph','12_path_finding','13_wire_protocol',
                '14_encrypted_transport','15_payment_requests','16_security_privacy_ln','17_conclusion']

    base_url = 'https://github.com/lnbook/lnbook/blob/develop/{}.asciidoc'
    print("Getting links for lightning book")
    chapter_links = scraper.get_github_urls(base_url,chapters)
    lndocs = scraper.parse_aantonop_books(chapter_links)
    print ("Number of documents: " + str(len(lndocs)))

    with open("lnbook.json", "w") as f:
      json.dump(lndocs, f, indent=4)

    # Close the file
    f.close()


if __name__ == "__main__":

  get_lightningbook_data()
