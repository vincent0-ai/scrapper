import os
import redis
from rq import Worker, Queue, Connection

from lyrics_scraper import search_song
from medium_scraper import MediumScraper
from proxy_scraper import scrape_and_save_proxies

listen = ['high', 'default', 'low']

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

conn = redis.from_url(redis_url)

def scrape_lyrics(query):
    """
    Scrapes for song lyrics.
    """
    return search_song(query)

def scrape_medium(url):
    """
    Scrapes a Medium article.
    """
    scraper = MediumScraper()
    return scraper.scrape_single(url)

def update_proxies():
    """
    Updates the proxy list.
    """
    scrape_and_save_proxies()


if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
