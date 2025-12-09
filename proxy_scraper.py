import requests
from bs4 import BeautifulSoup
from common import fetch_with_flaresolverr

def scrape_and_save_proxies(url="https://free-proxy-list.net/en/"):
    """
    Scrapes proxy list from a given URL and saves them to proxies.txt.
    """
    print(f"Fetching proxies from: {url}")
    try:
        html_content, _ = fetch_with_flaresolverr(url)
        if not html_content:
            raise requests.exceptions.RequestException("Failed to fetch content via FlareSolverr.")

        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", class_="table table-striped table-bordered")
        if not table or not table.tbody:
            print("Could not find proxy table on the page.")
            return

        with open("proxies.txt", "w", encoding="utf-8") as f:
            for row in table.tbody.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) > 1:
                    f.write(f"{cols[0].text.strip()}:{cols[1].text.strip()}\n")
        print(f"Proxies saved to proxies.txt")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching proxies: {e}")