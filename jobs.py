# jobs.py
from datetime import datetime
import json
import os
import logging
from typing import List
import requests

from scraper import scrape_articles, NewsArticle

# Keep your URL lists in one place
URLS = ["https://www.sme.sk/rss-title",
"https://dennikn.sk/feed", # https://dennikn.sk/rss-odber/
"https://spravy.pravda.sk/rss/xml/",
"https://www.aktuality.sk/rss/",
"https://www.hlavnespravy.sk/feed/", # gives file
"https://www.dobrenoviny.sk/rss", # file
"https://zive.aktuality.sk/rss/najnovsie/",
"https://www.news.sk/feed/",
"https://standard.sk/feed",
"https://spravy.stvr.sk/feed/", # file
"https://www.topky.sk/rss/10/Spravy_-_Domace.rss",
"https://hn24.hnonline.sk/hn24",
"https://www.postoj.sk/dnes-treba-vediet",
"https://tvnoviny.sk/prehlad-dna",
"https://www.noviny.sk/minuta-po-minute/e205daae-7500-483b-bb81-6728ce8a49c5",
"https://www.cas.sk/r/spravy"]

logger = logging.getLogger(__name__)

def serialize(articles: List[NewsArticle]):
    # Convert list[NewsArticle] -> list[dict] for JSON/upload
    return [a.__dict__ for a in articles]

def run_scrape_job() -> list[list[NewsArticle]]:
    """Scrape all feeds, write to dated file, return articles."""
    curr_date = datetime.now().strftime("%Y-%m-%d_%H:%M")
    os.makedirs("data/unlabelled", exist_ok=True)
    path = f"data/unlabelled/{curr_date}.txt"

    all_articles: list[list[NewsArticle]] = []
    with open(path, "a", encoding="utf-8") as f:  # append in case multiple runs/day
        for url in URLS:
            try:
                articles = scrape_articles(url)
                all_articles.extend(articles)
                logger.info("Scraped %d articles from %s", len(articles), url)
            except Exception as e:
                logger.exception("Failed scraping %s: %s", url, e)

        f.write("[")
        i = 0
        for article in all_articles:
            if i > 0:
                f.write(",")
            f.write(json.dumps(article.to_dict(), default=str, ensure_ascii=False))
            i += 1
        f.write("]")

    return all_articles

def maybe_upload(all_articles: list[list[NewsArticle]]) -> None:
    """Optionally POST results to a backend if configured."""
    endpoint = os.getenv("BACKEND_POST_URL", "").strip()
    if not endpoint:
        return

    headers = {"Content-Type": "application/json"}
    payload = {
        "batch_timestamp": datetime.utcnow().isoformat() + "Z",
        "feeds": [serialize(lst) for lst in all_articles],
    }
    timeout = float(os.getenv("BACKEND_TIMEOUT", "15"))

    # simple retry loop with backoff
    max_attempts = int(os.getenv("BACKEND_MAX_ATTEMPTS", "3"))
    backoff = float(os.getenv("BACKEND_BACKOFF_SECONDS", "2"))

    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=timeout)
            resp.raise_for_status()
            logger.info("Uploaded %d feeds to backend (%s)", len(payload["feeds"]), endpoint)
            return
        except Exception as e:
            logger.warning("Upload attempt %d/%d failed: %s", attempt, max_attempts, e)
            if attempt < max_attempts:
                import time
                time.sleep(backoff)
                backoff *= 2  # exponential
            else:
                logger.error("Giving up on upload after %d attempts.", max_attempts)
