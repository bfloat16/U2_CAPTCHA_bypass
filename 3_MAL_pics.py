import json
from tqdm import tqdm
import concurrent.futures
from bs4 import BeautifulSoup

from common import request_get_text

def fetch_anime_pics(anime):
    url = anime["url"]
    title = anime["title"]
    # 构造 pics 页面的 URL
    pics_url = url.rstrip("/") + "/pics"
    html = request_get_text(pics_url)
    soup = BeautifulSoup(html, "html.parser")
    pics = []
    # 查找所有符合条件的 <a> 标签
    for a_tag in soup.find_all("a", class_="js-picture-gallery", rel="gallery-anime"):
        img = a_tag.find("img")
        if img:
            src = img.get("data-src")
            if src and src not in pics:
                pics.append(src)
    return {"url": url, "title": title, "pics": pics}

if __name__ == '__main__':
    with open('2_MAL_url.json', 'r', encoding='utf-8') as f:
        anime_links = json.load(f)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
        future_to_anime = {executor.submit(fetch_anime_pics, anime): anime for anime in anime_links}
        with tqdm(total=len(future_to_anime)) as pbar:
            for future in concurrent.futures.as_completed(future_to_anime):
                result = future.result()
                results.append(result)

    with open('3_MAL_pics.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
