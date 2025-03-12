import re
import json
import requests
from bs4 import BeautifulSoup

from common import request_get_text

season_priority = {'winter': 1, 'fall': 2, 'summer': 3, 'spring': 4}

def extract_season_urls(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    season_urls = []
    
    pattern = re.compile(r'https://myanimelist\.net/anime/season/(\d{4})/(spring|summer|fall|winter)')
    
    seen_season_urls = set()
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if pattern.match(href) and href not in seen_season_urls:
            seen_season_urls.add(href)
            season_urls.append(href)
    
    return season_urls

def parse_season_url(url):
    match = re.search(r'(\d{4})/(spring|summer|fall|winter)', url)
    if match:
        year = int(match.group(1))
        season = match.group(2)
        return year, season
    return None, None


if __name__ == '__main__':
    html_content = request_get_text('https://myanimelist.net/anime/season/archive')
    season_urls = extract_season_urls(html_content)
    sorted_season_urls = sorted(season_urls, key=lambda url: (-parse_season_url(url)[0], season_priority[parse_season_url(url)[1]]))
    with open('1_MAL_index.json', 'w') as f:
        json.dump(sorted_season_urls, f, indent=4)