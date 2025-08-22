import requests
from bs4 import BeautifulSoup
from newspaper import Article
import trafilatura

class NewsArticle:
    """
    Object for accessing attributes of scraped articles.
    """
    def __init__(self, title, pub_date, link, source, content, image_link):
        """
        Creates object for accessing attributes of scraped articles.
        :param title: The article headline.
        :param pub_date: Article publication date.
        :param link: Article URL.
        :param source: URL of the news outlet.
        :param content: Plaintext of the article body - this is done through semantic scraping, so is not always accurate.
        :param image_link: Image URL.
        """
        self.title = title
        self.pub_date = pub_date
        self.link = link
        self.source = source
        self.content = content
        self.image_link = image_link

    def stringify(self):
        return (f"Headline: {self.title}\n"
                f"Publication date: {self.pub_date}\n"
                f"URL: {self.link}\n"
                f"Source: {self.source}\n"
                f"Content: {self.content}\n"
                f"Image link: {self.image_link}\n")

    def rowify(self):
        return f"{self.title},{self.pub_date},{self.link},{self.source},{self.content},{self.image_link}"

def scrape_articles(url, rss=True):
    """
    Scrapes all articles from the given RSS feed.
    # TODO - this only works for RSS feeds so far, and only was tested for sme.sk
    :param rss: TODO will be used as False when scraping news sources w.o. RSS feed
    :param url: The URL to be scraped.
    :return: A list of NewsArticle objects containing info on each article scraped.
    """
    articles = []
    response = requests.get(url)
    # print("url received")
    soup = BeautifulSoup(response.content, features="xml")
    # print(soup.prettify())
    items = soup.find_all("item")
    for item in items:
        headline = item.find("title").string
        emission_date = item.find("pubDate").string # TODO, may be different for other news outlets
        original_url = item.find("link").string
        image_link = find_main_image(item)
        article = Article(original_url)
        article.download()
        article.parse()
        # TODO there is also a .nlp() function, can explore what this does, could be useful
        # seems to provide a summary/basic semantic analysis
        source = article.source_url
        content = article.text
        if content.strip() == "":
            # print("using trafilatura")
            downloaded = trafilatura.fetch_url(original_url)
            content = trafilatura.extract(downloaded)

        # print(content)
        articles.append(NewsArticle(headline, emission_date, original_url, source, content, image_link))
        # articles[-1].print()

    return articles

def find_main_image(article):
    """
    Expects a BeautifulSoup parser object of the article.
    :param article:
    :return:
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