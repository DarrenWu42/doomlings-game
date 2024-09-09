'''
python script for scraping card data from Doomlings site
'''
from urllib import parse

import re
import requests

from argparse import ArgumentParser
from bs4 import BeautifulSoup, Tag

STARTING_URL = "https://www.worldofdoomlings.com/cards/echolocation"

INVISIBLE_CLASS = "w-condition-invisible"

parser = ArgumentParser(description="Scrapes card data from doomlings site")
parser.add_argument("-url", "--starting_url", type=str, default=STARTING_URL,
                    help="URL to begin ingestion at")
parser.add_argument("-i", "--images", action='store_true')
parser.add_argument("-d", "--data", action='store_true')
args = parser.parse_args()

def find_class(class_name):
    """function that, given a class name, returns a function to be used with beautiful soup that
    finds that class name

    Args:
        class_name (str): class name to find
    """
    def _f(class_):
        return class_ and re.compile(class_name+"(\\s|$)").search(class_)

    return _f

def retrieve_card_image(soup : BeautifulSoup, download_dir = "./images", img_name = "default"):
    """Downloads image for card into given directory.

    Args:
        soup (BeautifulSoup): BeautifulSoup object of a Doomlings page.
        dir (str, optional): Directory path to download images into. Defaults to "./images".
        img_name (str, optional): File name. Defaults to "default".

    Returns:
        bool: Success or failure (in the case of timeout or file writing error)
    """
    card_img : Tag = soup.find(class_=find_class("card-image-column")).a.img
    card_img_url = card_img["src"]

    try:
        card_img_res : requests.Response = requests.get(card_img_url, timeout=10)
    except requests.exceptions.Timeout:
        print(f"Timed out while retrieving picture for {img_name} from {card_img_url}")
        return False

    try:
        with open(f"{download_dir}/{img_name}.jpg", "wb") as file:
            file.write(card_img_res.content)
    except OSError:
        print(f"Failed while saving picture for {img_name} from {card_img_url}")
        return False

    return True

def retrieve_card_stats(card_properties_soup : BeautifulSoup):
    card_stats = {}

    card_stats_soup : BeautifulSoup = card_properties_soup.find(class_=find_class("card-stats"))
    for child in card_stats_soup.children:
        child : BeautifulSoup = child
        stats_key = list(filter(lambda c: c != INVISIBLE_CLASS, child["class"]))[0]
        property_pill_soups = child.find_all(class_=find_class("property-pill"))
        stats_value = [property_pill_soup.find_all("div")[-1].string
                        for property_pill_soup in property_pill_soups]
        card_stats[stats_key] = stats_value if len(stats_value) > 0 and stats_value[0] is not None \
                                    else []

    return card_stats

def retrieve_card_data(soup : BeautifulSoup):
    card_data = {}

    card_properties_soup : BeautifulSoup = soup.find(class_=find_class("card-properties-container"))
    card_data["card-stats"] = retrieve_card_stats(card_properties_soup)

    return card_data

def retrieve_next_url(soup : BeautifulSoup, base_url : str):
    next_block_soup : BeautifulSoup = soup.find(class_=find_class("next-block"))
    next_url_ref = next_block_soup.a["href"]

    return parse.urljoin(base_url, next_url_ref)

def main():
    """performs main scraping loop"""
    starting_url = args.starting_url
    parsed = parse.urlparse(starting_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    db = {}

    curr_url = starting_url

    while True:
        curr_name = curr_url.split("/")[-1]

        data = requests.get(curr_url, timeout=10).text
        data_soup = BeautifulSoup(data, features="html.parser")
        if args.images: retrieve_card_image(data_soup, img_name=curr_name)
        if args.data: db[curr_name] = retrieve_card_data(data_soup)
        curr_url = retrieve_next_url(data_soup, base_url)

        if curr_url == starting_url: break

main()
