import re
import json
from tqdm import tqdm
import concurrent.futures
from bs4 import BeautifulSoup

from common import request_get_text

def fetch_anime_links(season_url):
    html = request_get_text(season_url)
    soup = BeautifulSoup(html, 'html.parser')
    anime_links = []
    for h2 in soup.find_all('h2', class_='h2_anime_title'):
        a_tag = h2.find('a', class_='link-title')
        if a_tag and a_tag.get('href'):
            anime_links.append({
                "url": a_tag['href'],
                "title": a_tag.get_text(strip=True)
            })
    return anime_links

def extract_anime_id(url):
    match = re.search(r'/anime/(\d+)', url)
    if match:
        return int(match.group(1))
    return 0

if __name__ == '__main__':
    with open('1_MAL_index.json', 'r', encoding='utf-8') as f:
        season_urls = json.load(f)

    try:
        with open('2_MAL_url.json', 'r', encoding='utf-8') as f:
            existing_anime_links = json.load(f)
    except FileNotFoundError:
        existing_anime_links = []

    existing_set = set()
    for anime in existing_anime_links:
        existing_set.add((anime["url"], anime["title"]))

    new_anime_links = []
    stop_update = False

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_anime_links, url) for url in season_urls]
        with tqdm(total=len(season_urls)) as pbar:
            for season_url, future in zip(season_urls, futures):
                if stop_update:
                    break
                anime_links = future.result()
                for anime in anime_links:
                    key = (anime["url"], anime["title"])
                    if key in existing_set:
                        stop_update = True
                        break
                    new_anime_links.append(anime)
                pbar.update(1)

    full_anime_dict = {}
    for anime in new_anime_links + existing_anime_links:
        key = (anime["url"], anime["title"])
        full_anime_dict[key] = anime

    full_anime_links = list(full_anime_dict.values())
    full_anime_links.sort(key=lambda x: extract_anime_id(x["url"]), reverse=True)

    with open('2_MAL_url.json', 'w', encoding='utf-8') as f:
        json.dump(full_anime_links, f, indent=4, ensure_ascii=False)