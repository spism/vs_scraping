import requests
from bs4 import BeautifulSoup
from newspaper import Article
from newspaper.article import ArticleDownloadState
import trafilatura
import json


class NewsArticle:
    """
    Object for accessing attributes of scraped articles.
    """
    def __init__(self, title, pub_date, link, source, content, image_link, political_bias, economic_bias):
        """
        Creates object for accessing attributes of scraped articles.
        :param title: The article headline.
        :param pub_date: Article publication date.
        :param link: Article URL.
        :param source: URL of the news outlet.
        :param content: Plaintext of the article body - this is done through semantic scraping, so is not always accurate.
        :param image_link: Image URL.
        :param political_bias: Political bias of the article.
        :param economic_bias: Economic bias of the article.
        """
        self.title = title
        self.pub_date = pub_date
        self.link = link
        self.source = source
        self.content = content
        self.image_link = image_link
        self.political_bias = political_bias
        self.economic_bias = economic_bias

    def stringify(self):
        return (f"Headline: {self.title}\n"
                f"Publication date: {self.pub_date}\n"
                f"URL: {self.link}\n"
                f"Source: {self.source}\n"
                f"Content: {self.content}\n"
                f"Image link: {self.image_link}\n"
                f"Political bias: {self.political_bias}\n"
                f"Economic bias: {self.economic_bias}\n")

    def rowify(self):
        return f"{self.title},{self.pub_date},{self.link},{self.source},{self.content},{self.image_link},{self.political_bias},{self.economic_bias}"

def scrape_articles(url):
    """
    Scrapes all articles from the designated news url.
    List of working RSS URLs:
     - https://www.sme.sk/rss-title
     - https://dennikn.sk/feed
     - https://spravy.pravda.sk/rss/xml/
     - https://www.aktuality.sk/rss/
     - https://www.hlavnespravy.sk/feed/
     - https://www.dobrenoviny.sk/rss
     - https://zive.aktuality.sk/rss/najnovsie/
     - https://www.news.sk/feed/
     - https://standard.sk/feed
     - https://spravy.stvr.sk/feed/
     - https://www.topky.sk/rss/10/Spravy_-_Domace.rss
     Non-RSS:
     - https://hn24.hnonline.sk/hn24
     - https://www.postoj.sk/dnes-treba-vediet
     - https://tvnoviny.sk/prehlad-dna
     - https://www.noviny.sk/minuta-po-minute/e205daae-7500-483b-bb81-6728ce8a49c5
     - https://www.cas.sk/r/spravy
    # TODO - this only works for RSS feeds so far, and only was tested for sme.sk
    :param url: The URL to be scraped.
    :return: A list of NewsArticle objects containing info on each article scraped.
    """
    articles = []
    original_url = None
    response = requests.get(url)
    # print("url received")
    soup = BeautifulSoup(response.content, features="xml")
    rss_flag = soup.find("rss")
    # print(soup.prettify())

    if rss_flag is None:
        soup = BeautifulSoup(response.content, features="html.parser")
        items = soup.find_all("article")
    else:
        items = soup.find_all("item")

    # case where entire data is in json script element (cas.sk)
    if rss_flag is not None and len(items) == 0:
        script = soup.find("script", type="application/json")
        json_data = json.loads(script.string)
        articles_json = json_data["props"]["pageProps"]["initialState"]["data"]["articles"]
        for json_article in articles_json:
            # print(raw_article["content"])
            # TODO maybe have another for loop which goes over all located links, using newspaper3k to get other article stuff
            # - this could be faster
            original_url = json_article["content"]["mainRoute"]["domain"] + json_article["content"]["mainRoute"]["path"]
            article = Article(original_url)
            article.download()
            article.parse()
            headline = article.title
            emission_date = article.publish_date
            image_link = article.top_image
            source = article.source_url
            content = article.text
            if content.strip() == "":
                downloaded = trafilatura.fetch_url(original_url)
                content = trafilatura.extract(downloaded)

            articles.append(NewsArticle(headline, emission_date, original_url, source, content, image_link, None, None))

    for item in items:
        if rss_flag is None:
            article_elements = item.find_all("a", href=True)
            if len(article_elements) > 0:
                if article_elements[0]["href"][0] == "/":
                    original_url = url + article_elements[0]["href"]
                elif (len(article_elements) > 1 and "class" in article_elements[0] and len(article_elements[0]["class"]) > 1
                      and article_elements[0]["class"][0] == "img" and article_elements[0]["class"][1] == "js-live-box-link"):
                    continue
                elif len(article_elements) > 1 and "class" in article_elements[0] and article_elements[0]["class"] == "img":
                    original_url = article_elements[1]["href"]
                else:
                    original_url = article_elements[0]["href"]
        else:
            original_url = item.find("link").string
            headline = item.find("title").string
            emission_date = item.find("pubDate").string
            image_link = find_main_image(item)

        if original_url is not None:
            article = Article(original_url)
            article.download()
            if article.download_state == ArticleDownloadState.FAILED_RESPONSE or article.download_state == ArticleDownloadState.NOT_STARTED:
                continue
            article.parse()
            # TODO there is also a .nlp() function, can explore what this does, could be useful
            # seems to provide a summary/basic semantic analysis
            if rss_flag is None:
                headline = article.title
                emission_date = article.publish_date
                image_link = article.top_image

            source = article.source_url
            content = article.text
            if content.strip() == "":
                downloaded = trafilatura.fetch_url(original_url)
                content = trafilatura.extract(downloaded)

            # assert(headline is not None and emission_date is not None and image_link is not None)
            articles.append(NewsArticle(headline, emission_date, original_url, source, content, image_link, None, None))

    return articles

def find_main_image(article):
    """
    Expects a BeautifulSoup parser object of the article.  Finds the primary image of an RSS item article.
    :param article: The article in question.
    :return: The image link of the article.
    """
    if article.find("enclosure") is not None and (article.find("enclosure")["type"] == "image/jpeg"
            or article.find("enclosure")["type"] == "image/png" or article.find("enclosure")["type"] == "image/webp"):
        # print("enclosure")
        return article.find("enclosure")["url"]

    if article.find("image:url") is not None:
        # print("image:url")
        return article.find("image:url").string

    if article.find("media:content") is not None and article.find("media:content")["medium"] == "image":
        # print("media:content")
        return article.find("media:content")["url"]

    # case where none of the above could be located = resort to manual scraping
    # print("manual scrape")
    fulltext = requests.get(article.find("link").string)
    soup = BeautifulSoup(fulltext.content, features="html.parser")
    # print(soup.prettify)
    # in case of standard.sk
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img["content"]:
        # print(og_img["content"])
        return og_img["content"]