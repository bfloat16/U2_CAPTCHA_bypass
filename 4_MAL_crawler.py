import os
import re
import json
from tqdm import tqdm
import concurrent.futures

from common import get_binary_content

def extract_anime_id(anime_url):
    match = re.search(r'/anime/(\d+)', anime_url)
    if match:
        return match.group(1)
    return None

def extract_image_id(image_url):
    match = re.search(r'/(\d+)\.jpg', image_url)
    if match:
        return match.group(1)
    return None

def download_and_save_image(image_url, filename):
    folder = "images"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        return filename

    content = get_binary_content(image_url)
    with open(file_path, 'wb') as f:
        f.write(content)
    return filename

if __name__ == '__main__':
    with open('3_MAL_pics.json', 'r', encoding='utf-8') as f:
        anime_list = json.load(f)

    tasks = []
    for anime in anime_list:
        anime_id = extract_anime_id(anime["url"])
        if not anime_id:
            continue
        for img_url in anime.get("pics", []):
            image_id = extract_image_id(img_url)
            if not image_id:
                continue
            filename = f"{anime_id}_{image_id}.jpg"
            tasks.append((img_url, filename))

    total_tasks = len(tasks)

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_task = {executor.submit(download_and_save_image, img_url, filename): (img_url, filename) for img_url, filename in tasks}
        with tqdm(total=total_tasks) as pbar:
            for future in concurrent.futures.as_completed(future_to_task):
                img_url, filename = future_to_task[future]
                future.result()
                pbar.update(1)