import scraper
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from datetime import datetime
app = Flask(__name__)

rss_urls = ["https://www.sme.sk/rss-title",
"https://dennikn.sk/feed", # https://dennikn.sk/rss-odber/
"https://spravy.pravda.sk/rss/xml/",
"https://www.aktuality.sk/rss/",
"https://www.hlavnespravy.sk/feed/", # gives file
"https://www.dobrenoviny.sk/rss", # file
"https://zive.aktuality.sk/rss/najnovsie/",
"https://www.news.sk/feed/",
"https://standard.sk/feed",
"https://spravy.stvr.sk/feed/"] # file

non_rss_urls = ["https://hnonline.sk/",
"https://www.postoj.sk/",
"https://www.startitup.sk/",
"https://tvnoviny.sk/",
"https://www.noviny.sk/",
"https://www.topky.sk/",
"https://www.cas.sk/"]

def check_all_rss_versions_2():
    for url in rss_urls:
        feed = requests.get(url)
        soup = BeautifulSoup(feed.content, features="xml")
        rss_ver = soup.find("rss")['version']
        if rss_ver != "2.0":
            return False
    return True

def check_all_have_image():
    for url in rss_urls:
        print(url)
        feed = requests.get(url)
        soup = BeautifulSoup(feed.content, features="xml")
        items = soup.find_all("item")
        for item in items:
            if scraper.find_main_image(item) is None:
                return False
    return True

def test_guid_format(guid):
    split_guid = guid.split("-")

@app.route("/scrape",methods=["GET"])
def scrape_endpoint():
    print("Scraping started")
    curr_date = datetime.today().strftime('%Y-%m-%d')
    file = open(f"data/unlabelled/{curr_date}", "w+", encoding="utf-8")
    all_articles = []

    for url in rss_urls:
        articles = scraper.scrape_articles(url)
        print("Writing to file...")
        for article in articles:
            file.write(article.stringify())
        all_articles.append(articles)

    return jsonify(all_articles)


if __name__ == '__main__':
    app.run(debug=True)
    # print(check_all_have_image())
    # feed = requests.get(rss_urls[5], allow_redirects=True)
    # soup = BeautifulSoup(feed.content, features="xml")
    # print(soup.prettify())
    # articles = scraper.scrape_articles(rss_urls[0])
    # print(articles[0].stringify())
    # for url in rss_urls:
    #     articles = scraper.scrape_articles(url)