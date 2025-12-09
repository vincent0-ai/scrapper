import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
import random
import os
import requests
from bs4 import BeautifulSoup

def get_random_proxy():
    """Reads proxies from proxies.txt and returns a random one."""
    try:
        with open("proxies.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
        if proxies:
            return random.choice(proxies)
    except FileNotFoundError:
        print("proxies.txt not found. Continuing without proxy.")
    return None


class MediumScraper:
    def __init__(self, concurrency: int = 4, flaresolverr_url: str = os.getenv("FLARE_URL")):
        self.concurrency = concurrency
        self.session = requests.Session()
        self.flaresolverr_url = flaresolverr_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def fetch_html(self, url: str) -> str:
        proxy = get_random_proxy()
        proxies = None
        if proxy:
            proxies = {
                "http": f"http://{proxy}",
                "https": f"http://{proxy}",
            }
            print(f"Using proxy: {proxy}")

        try:
            resp = self.session.get(url, headers=self.headers, timeout=20, proxies=proxies)
            resp.raise_for_status()
            return resp.text
        except Exception:
            payload = {"cmd": "request.get", "url": url, "maxTimeout": 60000}
            if proxy:
                # The proxy format for FlareSolverr is http://user:pass@host:port
                # Assuming proxies do not require authentication.
                payload["proxy"] = f"http://{proxy}"
            r = requests.post(self.flaresolverr_url, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            return data.get("solution", {}).get("response", "")

    def parse_article(self, html: str) -> Dict:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1")
        title_text = title.get_text(strip=True) if title else ""
        author_text = ""
        if author_tag := soup.find("meta", attrs={"name": "author"}):
            author_text = author_tag.get("content", "")
        publish_text = ""
        if publish_tag := soup.find("meta", attrs={"property": "article:published_time"}):
            publish_text = publish_tag.get("content", "")
        tags = [t.get_text(strip=True) for t in soup.find_all("a", attrs={"data-testid": "topicTag"})]
        paragraphs = soup.find_all("p")
        content = "".join(p.get_text(strip=True) for p in paragraphs)
        return {"title": title_text, "author": author_text, "published": publish_text, "tags": tags, "content": content}

    def scrape_single(self, url: str) -> Dict:
        html = self.fetch_html(url)
        data = self.parse_article(html)
        data["url"] = url
        return data

    def scrape_bulk(self, urls: List[str]) -> List[Dict]:
        results: List[Dict] = []
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {executor.submit(self.scrape_single, u): u for u in urls}
            for f, u in futures.items():
                try:
                    results.append(f.result())
                except Exception as e:
                    results.append({"error": str(e), "url": u})
        return results

    def save_json(self, data: List[Dict], filename: str):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    scraper = MediumScraper()
    url = input("Enter a Medium article URL (e.g., https://medium.com/.../...): ").strip()
    result = scraper.scrape_single(url)
    scraper.save_json([result], "article.json")
