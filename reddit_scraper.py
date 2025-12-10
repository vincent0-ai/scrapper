from bs4 import BeautifulSoup
from urllib.parse import urlparse
from common import fetch_with_flaresolverr
from db import db_manager

class RedditScraper:
    def scrape_single(self, url):
        # Check DB first
        cached_data = db_manager.get_reddit_thread(url)
        if cached_data:
            cached_data.pop('_id', None)
            return cached_data

        # Ensure we use old.reddit.com for easier HTML parsing
        parsed = urlparse(url)
        # Replace domain with old.reddit.com
        scrape_url = parsed._replace(netloc='old.reddit.com').geturl()

        html_content, _ = fetch_with_flaresolverr(scrape_url)
        if not html_content:
            return {"error": "Failed to fetch Reddit content."}

        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract Post Data
        site_table = soup.find("div", id="siteTable")
        if not site_table:
             return {"error": "Could not find post content structure."}
             
        thing = site_table.find("div", class_="thing")
        if not thing:
             return {"error": "Could not find post element."}

        title_elm = thing.find("a", class_="title may-blank loggedin")
        title = title_elm.get_text(strip=True) if title_elm else "Unknown Title"
        
        author_elm = thing.find("p", class_="tagline")
        author = author_elm.get_text(strip=True) if author_elm else "Unknown Author"
        
        entry = thing.find("div", class_="entry unvoted")
        usertext = entry.find("div", class_="usertext-body may-blank-within md-container ") if entry else None
        content = usertext.get_text("\n", strip=True) if usertext else ""

        if not title or not author or not content:
            return {"error": "Could not find post content."}

        result = {"title": title, "author": author, "content": content, "url": url}
        db_manager.save_reddit_thread(url, result)
        return result