import time
import schedule
from proxy_scraper import scrape_and_save_proxies

def job():
    print("Running proxy scraping job...")
    scrape_and_save_proxies()
    print("Proxy scraping job finished.")

schedule.every(4).hours.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)