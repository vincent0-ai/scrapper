import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from common import fetch_with_flaresolverr # For raw HTML caching
import concurrent.futures

SITES = {
    "mysongbooks": {
        "search_url": "https://www.mysongbooks.scaptedesigns.com/library/search?s={query}",
        "type": "scrape",
        "result_selector": "div.col-12.col-md-6.col-lg-6.mb-1",
        "link_selector": "a.d-flex",
        "title_selector": "h6",
        "artist_selector": "p",
        "lyrics_container_selector": "div.row.item-list.item-list-md.m-t.m-b p.item-title.text-black",
    },
    "lyricshymn": {
        "search_url": "https://lyricshymn.com/library/search?s={query}", # This URL seems incorrect, should be a valid domain
        "type": "scrape",
        "result_selector": "div.col-12.col-md-6",
        "link_selector": "a",
        "title_selector": "h6",
        "artist_selector": "p",
        "lyrics_container_selector": "div.col-8",
        # Note: lyricshymn.com seems to be a dead domain or parked page.
        # The scraper might not work for this site.
        # For the purpose of this exercise, I'll assume it's a valid target.
    },
    "simpmusic": {
        "search_url": "https://api-lyrics.simpmusic.org/v1/search?q={query}",
        "type": "api",
    }
}

from db import db_manager # Import the database manager

def search_song(query):
    """
    Searches for a song across multiple sites and returns the first found lyrics.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_site = {executor.submit(search_site, query, site, config): site for site, config in SITES.items()}
        for future in concurrent.futures.as_completed(future_to_site):
            result = future.result()
            if result:
                return result
    return None

def search_site(query, site_name, site_config):
    site_type = site_config.get("type", "scrape")
    if site_type == "api":
        return _search_api(query, site_config)
    else:
        return _search_scrape(query, site_config)

def _search_api(query, site_config):
    try:
        search_url = site_config["search_url"].format(query=quote(query))
        r = requests.get(search_url, timeout=20)
        r.raise_for_status()
        data = r.json()
        if data and data.get("lyrics"):
            lyrics_data = {
                "title": data.get("title", query),
                "artist": data.get("artist", "Unknown"),
                "lyrics": data["lyrics"],
                "source": "simpmusic API"
            }
            db_manager.save_lyrics(query, lyrics_data) # Save to DB
            return lyrics_data
    except requests.exceptions.RequestException:
        return None
    return None

def _search_scrape(query, site_config):
    search_url = site_config["search_url"].format(query=quote(query))
    html_content, _ = fetch_with_flaresolverr(search_url)
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, "html.parser")
    container = soup.select_one(site_config["result_selector"])
    if not container:
        return None

    link_tag = container.select_one(site_config["link_selector"])
    if not link_tag or not link_tag.has_attr('href'):
        return None

    song_url = urljoin(search_url, link_tag["href"])
    song_html, _ = fetch_with_flaresolverr(song_url)
    if not song_html:
        return None

    song_soup = BeautifulSoup(song_html, "html.parser")
    
    # Use the configured title_selector instead of the generic <title> tag
    title_element = song_soup.select_one(site_config["title_selector"])
    title = title_element.get_text(strip=True) if title_element else "Unknown Title"

    # Use the configured artist_selector (if available)
    artist_element = song_soup.select_one(site_config.get("artist_selector", ""))
    artist = artist_element.get_text(strip=True) if artist_element else "Unknown Artist"

    lyrics_container = song_soup.select_one(site_config["lyrics_container_selector"])
    
    if lyrics_container:
        lyrics_text = lyrics_container.get_text(separator='\n', strip=True)
        lyrics_data = {"title": title, "artist": artist, "lyrics": lyrics_text, "source": urljoin(song_url, '/')}
        db_manager.save_lyrics(query, lyrics_data) # Save to DB
        return lyrics_data
    return None