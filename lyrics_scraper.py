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
    },
    "sifalyrics": {
        "search_url": "https://www.sifalyrics.com/search?q={query}",
        "type": "scrape",
        "result_selector": "article.card.wow.fadeInLeft.animation-delay-5.mb-4",
        "link_selector": "a",
        "title_selector": "h3.a",
        "artist_selector": "h3.a",
        "lyrics_container_selector": "div.material-card",
    },
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
    return _search_scrape(query, site_config)

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
    artist_selector = site_config.get("artist_selector")
    artist_element = song_soup.select_one(artist_selector) if artist_selector else None
    artist = artist_element.get_text(strip=True) if artist_element else "Unknown Artist"

    lyrics_container = song_soup.select_one(site_config["lyrics_container_selector"])
    
    if lyrics_container:
        lyrics_text = lyrics_container.get_text(separator='\n', strip=True)
        lyrics_data = {"title": title, "artist": artist, "lyrics": lyrics_text, "source": urljoin(song_url, '/')}
        db_manager.save_lyrics(query, lyrics_data) # Save to DB
        return lyrics_data
    return None

def search_simpmusic_only(query, search_type="song"):
    """
    Dedicated function to search SimpMusic API.
    """
    base_url = "https://api-lyrics.simpmusic.org/v1/search"

    if search_type == "artist":
        url = f"{base_url}/artist"
        params = {"artist": query}
    elif search_type == "title" or search_type == "song":
        url = f"{base_url}/title"
        params = {"title": query}
    else:
        url = base_url
        params = {"q": query}

    try:
        # Using requests params to handle encoding and query construction
        r = requests.get(url, params=params, timeout=45)
        r.raise_for_status()
        data = r.json()
        
        if data.get("success") and data.get("data") and len(data["data"]) > 0:
            first_result = data["data"][0]
            lyrics_data = {
                "title": first_result.get("songTitle", query),
                "artist": first_result.get("artistName", "Unknown"),
                "lyrics": first_result.get("plainLyric", ""),
                "source": "SimpMusic API"
            }
            
            if lyrics_data["lyrics"]:
                db_manager.save_lyrics(query, lyrics_data)
                return lyrics_data

        return {"error": "No lyrics found via SimpMusic API."}
    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
            if e.response.status_code == 429:
                return {"error": "SimpMusic API Rate Limit Exceeded. Please try again later."}
            if e.response.status_code == 503:
                return {"error": "SimpMusic API Service Unavailable. Please try again later."}
            if e.response.status_code == 404:
                return {"error": "No lyrics found via SimpMusic API."}
        return {"error": f"SimpMusic API Error: {str(e)}"}