from bs4 import BeautifulSoup
from urllib.parse import urlparse
from common import fetch_with_flaresolverr
from db import db_manager

class RedditScraper:
    def scrape_single(self, url):
        # Check cache
        cached_data = db_manager.get_reddit_thread(url)
        if cached_data:
            cached_data.pop("_id", None)
            return cached_data

        # Force old.reddit.com
        parsed = urlparse(url)
        scrape_url = parsed._replace(netloc="old.reddit.com").geturl()

        # Fetch HTML
        data = fetch_with_flaresolverr(scrape_url)
        html_content = data.get("solution", {}).get("response")
        if not html_content:
            return {"error": "Failed to fetch Reddit content."}

        soup = BeautifulSoup(html_content, "html.parser")

        # Find main post container
        site_table = soup.find("div", id="siteTable")
        if not site_table:
            return {"error": "Could not find post content structure."}

        # Find post element ("thing")
        thing = site_table.find("div", class_="thing")
        if not thing:
            return {"error": "Could not locate post element."}

        # Title
        title_elm = thing.find("a", class_="title")
        title = title_elm.get_text(strip=True) if title_elm else "Unknown Title"

        # Author
        tagline = thing.find("p", class_="tagline")
        author = tagline.get_text(strip=True) if tagline else "Unknown Author"

        # Content (selftext)
        entry = thing.find("div", class_="entry")
        usertext = entry.select_one("div.usertext-body") if entry else None
        content = usertext.get_text("\n", strip=True) if usertext else ""

        result = {
            "title": title,
            "author": author,
            "content": content,
            "url": url
        }

        db_manager.save_reddit_thread(url, result)
        return result
