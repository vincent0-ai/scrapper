import os
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from common import fetch_with_flaresolverr, get_random_proxy
from db import db_manager


class FreediumScraper:
    def __init__(self, concurrency: int = 4):
        self.concurrency = concurrency
        self.flaresolverr_url = os.getenv("FLARE_URL")
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def parse_article(self, html: str) -> Dict:
        soup = BeautifulSoup(html, "html.parser")

        # Title
        title_tag = soup.find("h1", class_ = "pt-6 pb-2 font-sans text-3xl font-bold text-gray-900 break-normal dark:text-gray-100 md:text-4xl")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Author
        author = ""
        if author_tag := soup.find("a", class_="block font-semibold text-gray-900 dark:text-white __web-inspector-hide-shortcut__"):
            author = author_tag.get("href", "")
        else:
            # Freedium sometimes puts the author in a link with rel=author
            if a := soup.find("a", rel="author"):
                author = a.get_text(strip=True)
            else:
                return None  # Cannot find author, likely not a valid Freedium article


        # Content: prefer <article> or common post container classes
        content_container = soup.find("article") or soup.find("div", class_="mt-8 main-content") or soup.find("div", class_="content")
        if content_container:
            paragraphs = content_container.find_all(["p", "h2", "h3", "li"])  # include headings and list items
            content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        else:
            # fallback to all paragraphs
            content = "\n\n".join(p.get_text(strip=True) for p in soup.find_all("p"))

        return {"title": title, "author": author, "content": content}

    def scrape_single(self, url: str) -> Dict:
        # Check DB cache first
        cached = db_manager.get_article(url)
        if cached:
            cached.pop("_id", None)
            return cached

        html, _ = fetch_with_flaresolverr(url)
        if not html:
            return {"error": "Failed to fetch article content."}

        article = self.parse_article(html)
        article["url"] = url
        db_manager.save_article(url, article)
        return article

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
