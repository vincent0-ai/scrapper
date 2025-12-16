import os
import random
import requests
import hashlib
import json
import time  # Keep time for file cache
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv is optional; if not installed, rely on environment variables
    pass


FLARE = os.environ.get("FLARE_URL") # FlareSolverr URL
CACHE_DIR = "cache"
TTL = 3600  # 1 hour

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

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

def _key_to_file(url):
    h = hashlib.sha256(url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, h + ".json")

def _load_cache(url):
    path = _key_to_file(url)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if time.time() - data["timestamp"] > TTL:
        return None
    return data["html"], data["cookies"]

def _save_cache(url, html, cookies):
    path = _key_to_file(url)
    data = {"timestamp": time.time(), "html": html, "cookies": cookies}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

def fetch_with_flaresolverr(url):
    cached_data = _load_cache(url) # This cache is for raw HTML, separate from DB
    if cached_data:
        return cached_data

    # Retry mechanism to handle bad proxies and timeouts
    max_retries = 3
    for attempt in range(max_retries):
        proxy = get_random_proxy()
        payload = {"cmd": "request.get", "url": url, "maxTimeout": 30000}
        if proxy:
            payload["proxy"] = f"http://{proxy}"

        try:
            # Increased timeout to 60s to exceed FlareSolverr's maxTimeout of 30s
            r = requests.post(FLARE, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "ok":
                html, cookies = data["solution"]["response"], data["solution"]["cookies"]
                _save_cache(url, html, cookies)
                return html, cookies
            # If FlareSolverr returns not ok, fallback to direct request
            print(f"FlareSolverr returned non-ok status (attempt {attempt+1}/{max_retries}), falling back to direct request")
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with FlareSolverr (attempt {attempt+1}/{max_retries}): {e}, falling back to direct request")

        # Fallback to direct request
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            proxies = None
            if proxy:
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            r = requests.get(url, headers=headers, proxies=proxies, timeout=30)
            r.raise_for_status()
            html = r.text
            cookies = dict(r.cookies)
            _save_cache(url, html, cookies)
            return html, cookies
        except requests.exceptions.RequestException as e:
            print(f"Direct request also failed (attempt {attempt+1}/{max_retries}): {e}")
            
    return None, None
