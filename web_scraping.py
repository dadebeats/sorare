import argparse
import csv
import time
from enum import Enum
import re
import os
import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

parser = argparse.ArgumentParser()
parser.add_argument("out_filepath", type=str, help="Where to write the data.")


class SearchResult(Enum):
    NO_PRICE = -1
    FAILED_SEARCH = -2


def get_market_price(browser, slug):
    browser.get("https://www.google.com/")
    search = browser.find_element(by=By.NAME, value="q")
    search.clear()
    search.send_keys("transfermarkt " + slug)
    search.send_keys(Keys.RETURN)
    time.sleep(0.2)
    assert "No results found." not in browser.page_source

    price_available = False
    try:
        browser.find_elements(by=By.CLASS_NAME, value='yuRUbf')[0].click()  # clicks the first google search link
        time.sleep(0.2)
        price = browser.find_element(by=By.CLASS_NAME,
                                     value="tm-player-market-value-development__current-value"
                                     ).text
        price_available = True
    except:
        print("Failed search")
        price = SearchResult.FAILED_SEARCH

    if price_available:
        if "." in price:
            x = price.split(".")
            whole = x[0]
            decimal = x[1]
        elif "," in price:
            x = price.split(",")
            whole = x[0]
            decimal = x[1]
        else:
            whole = price
            decimal = ""

        whole = re.sub("[^0-9]", "", whole)
        decimal = re.sub("[^0-9]", "", decimal)
        if len(whole) > 0:
            if "Th." in price or "Tsd." in price:
                price = float(whole) * 1000  # truncate the decimal part
            elif "m" in price or "Mio." in price:
                price = float(whole) * 1_000_000
                if len(decimal) > 0:
                    price += float(decimal) * 10 ** (6 - len(decimal))
        else:
            price = SearchResult.NO_PRICE

    if type(price) is SearchResult:
        price = price.value

    return price


def main(args: argparse.Namespace):
    out_filepath = args.out_filepath

    options = webdriver.ChromeOptions()
    chrome_prefs = {}
    options.experimental_options["prefs"] = chrome_prefs
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--test-type")
    options.add_argument("start-maximized")
    options.add_argument("enable-automation")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-browser-side-navigation")
    options.add_argument("--disable-gpu")
    chrome_prefs["profile.default_content_settings"] = {"popups": 1}

    browser = webdriver.Chrome("chromedriver.exe", chrome_options=options)
    browser.get("https://www.google.com/")
    browser.find_element(value="L2AGLb").click()  # accepts the cookies button

    # TODO: neresit jako len(line) > 0, ale pres playground projit csv a upravit (vyhazet prazdny radky, coache)
    with open("../data/all_players_simple.csv", "r") as f:
        slugs = [line[0] for line in csv.reader(f) if len(line) > 0][1:]

    if os.path.exists(out_filepath):
        prices = json.load(open(out_filepath, "r"))
        already_done_slugs = set(prices.keys())
        slugs = [slug for slug in slugs if slug not in already_done_slugs]
    else:
        prices = {}

    for slug in slugs:
        prices[slug] = get_market_price(browser, slug)
        json.dump(prices, open(out_filepath, "w"))


if __name__ == "__main__":
    args = parser.parse_args([] if "__file__" not in globals() else None)
    main(args)
