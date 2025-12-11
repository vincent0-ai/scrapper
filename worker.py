import os
import redis
from rq import Worker, Queue

from lyrics_scraper import search_song, search_simpmusic_only
from medium_scraper import MediumScraper
from proxy_scraper import scrape_and_save_proxies

listen = ['high', 'default', 'low']

redis_url = os.getenv('REDIS_URL')

conn = redis.from_url(redis_url)

def scrape_lyrics(query):
    """
    Scrapes for song lyrics.
    """
    return search_song(query)

def search_simpmusic(query, search_type):
    """
    Searches SimpMusic API specifically.
    """
    return search_simpmusic_only(query, search_type)

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
    return scrape_and_save_proxies()


if __name__ == '__main__':
    queues = [Queue(q, connection=conn) for q in listen]
    worker = Worker(queues, connection=conn)
    worker.work()
