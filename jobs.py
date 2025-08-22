# jobs.py
from datetime import datetime
import json
import os
import logging
from typing import List
import requests

from scraper import scrape_articles, NewsArticle

# Keep your URL lists in one place
RSS_URLS = [
    "https://www.sme.sk/rss-title",
    "https://dennikn.sk/feed",
    "https://spravy.pravda.sk/rss/xml/",
    "https://www.aktuality.sk/rss/",
    "https://www.hlavnespravy.sk/feed/",
    "https://www.dobrenoviny.sk/rss",
    "https://zive.aktuality.sk/rss/najnovsie/",
    "https://www.news.sk/feed/",
    "https://standard.sk/feed",
    "https://spravy.stvr.sk/feed/",
]

logger = logging.getLogger(__name__)

def serialize(articles: List[NewsArticle]):
    # Convert list[NewsArticle] -> list[dict] for JSON/upload
    return [a.__dict__ for a in articles]

def run_scrape_job() -> list[list[NewsArticle]]:
    """Scrape all feeds, write to dated file, return articles."""
    curr_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    os.makedirs("data/unlabelled", exist_ok=True)
    path = f"data/unlabelled/{curr_date}.txt"

    all_articles: list[list[NewsArticle]] = []
    with open(path, "a", encoding="utf-8") as f:  # append in case multiple runs/day
        for url in RSS_URLS:
            try:
                articles = scrape_articles(url)
                for article in articles:
                    f.write(article.stringify() + "\n")
                all_articles.append(articles)
                logger.info("Scraped %d articles from %s", len(articles), url)
            except Exception as e:
                logger.exception("Failed scraping %s: %s", url, e)

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
