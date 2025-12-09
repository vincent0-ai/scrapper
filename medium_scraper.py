import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from common import fetch_with_flaresolverr, get_random_proxy  # Import common utilities
from db import db_manager # Import the database manager
 # Adjust as needed


class MediumScraper:
    def __init__(self, concurrency: int = 4):
        self.concurrency = concurrency
        self.flaresolverr_url = "http://flaresolve.captain.echowithin.xyz:8191/v1" 
        self.session = requests.Session()
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
        
        # More robust content extraction for Medium articles
        article_body = soup.find("article") or soup.find("div", class_="postArticle-content")
        if article_body:
            paragraphs = article_body.find_all("p")
            content = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            # Fallback if specific article body selectors don't work
            content = "\n\n".join(p.get_text(strip=True) for p in soup.find_all("p"))
            
        return {"title": title_text, "author": author_text, "published": publish_text, "tags": tags, "content": content}

    def scrape_single(self, url: str) -> Dict:
        # Check DB first
        cached_article = db_manager.get_article(url)
        if cached_article:
            cached_article.pop('_id', None) # Remove MongoDB's internal _id field
            return cached_article

        # If not in DB, scrape using the common utility
        html_content, _ = fetch_with_flaresolverr(url) # Use the new method
        if not html_content:
            return {"error": "Failed to fetch article content."}
        
        article_data = self.parse_article(html_content)
        article_data["url"] = url
        
        db_manager.save_article(url, article_data) # Save to DB
        return article_data

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
