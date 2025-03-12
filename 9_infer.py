import re
import bs4
import torch
import urllib
from PIL import Image
from io import BytesIO
from ultralytics import YOLO
from transformers import AutoImageProcessor, AutoModel
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import request_get_binary, request_get_text, retry


def fetch_image(url):
    """Download image from URL and return title with decoded image."""
    img = request_get_binary(url)
    image = Image.open(BytesIO(img)).convert("RGB")
    return image


@retry
def fetch_anime_images_url(anime_name):
    """Search MAL for the given anime name and return the URL of its pics page."""
    encoded_name = urllib.parse.quote(anime_name)
    search_url = f"https://myanimelist.net/anime.php?cat=all&q={encoded_name}"
    print("Searching MAL:", search_url)
    search_page = request_get_text(search_url)
    soup = bs4.BeautifulSoup(search_page, "html.parser")
    
    first_link = soup.find('a', class_=re.compile(r'^hoverinfo_trigger'))
    if first_link is None:
        raise Exception("No search result found for: " + anime_name)
    
    anime_url = first_link['href'] + "/pics"
    return anime_url


@retry
def fetch_anime_images(anime_url):
    """Fetch image URLs and their titles from the given MAL pics page URL."""
    pics_page = request_get_text(anime_url)
    soup = bs4.BeautifulSoup(pics_page, "html.parser")
    
    image_urls = []
    a_tags = soup.find_all("a", class_="js-picture-gallery", rel="gallery-anime")
    if not a_tags:
        raise Exception("No images found at " + anime_url)
    for a_tag in a_tags:
        img_tag = a_tag.find("img")
        if not img_tag:
            raise Exception("Image tag not found in one of the results")
        img_url = img_tag.get("data-src")
        if img_url not in image_urls:
            image_urls.append((img_url))
    return image_urls

@retry
def get_verification_info():
    """
    Visit the verification URL to get the CAPTCHA image and the
    associated question values.
    """
    url = "https://u2.dmhy.org/image.php?action=reload_adbc2&amp;div=showup&amp"
    response = request_get_text(url)
    soup = bs4.BeautifulSoup(response, "html.parser")
    
    # Get CAPTCHA image src
    img = soup.find("img")
    if not img:
        raise Exception("Verification image not found.")
    img_src = "https://u2.dmhy.org/" + img["src"]
    
    # Clean up the submit input values (questions)
    submit_inputs = soup.find_all("input", {"type": "submit"})
    submit_values = [inp.get("value") for inp in submit_inputs]
    clean_values = [f"{i + 1}_+_{value.split(' / ')[0].replace('.hack//', '')}" for i, value in enumerate(submit_values)]
    submit_values = [f"{i + 1}_+_{value}" for i, value in enumerate(submit_values)]
    
    print("Verification image src:")
    print(img_src, "\n")
    print("Verification submit values:")
    for value in submit_values:
        print(value)
    print("\n")
    print("Verification clean values:")
    for value in clean_values:
        print(value)
    print("\n")
    return img_src, clean_values, submit_values

def process_detection_results(results, image):
    """
    Process YOLO detection results:
    - Choose the best box per class (0: circle, 1/2: rectangles)
    - Crop the detected rectangles and determine which one contains the circle
    """
    best_boxes = {}
    center_x, center_y = None, None
    cropped_img1 = None
    cropped_img2 = None

    for result in results:
        for box in result.boxes:
            cls = int(box.cls.item())
            conf = float(box.conf.item())
            if cls not in best_boxes or conf > best_boxes[cls]["conf"]:
                best_boxes[cls] = {"box": box, "conf": conf}
    
    for cls, data in best_boxes.items():
        box = data["box"]
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        if cls == 0:
            center_x, center_y = cx, cy
            print(f"Detected circle at: ({cx}, {cy})")
        elif cls == 1:
            cropped_img1 = image.crop((x1, y1, x2, y2))
            print(f"Detected rectangle (cls=1) at: ({cx}, {cy})")
        elif cls == 2:
            cropped_img2 = image.crop((x1, y1, x2, y2))
            print(f"Detected rectangle (cls=2) at: ({cx}, {cy})")
    
    # Determine which rectangle contains the circle
    belongs_to = None
    if center_x is not None and center_y is not None:
        for cls in [1, 2]:
            if cls in best_boxes:
                x1, y1, x2, y2 = map(int, best_boxes[cls]["box"].xyxy[0])
                if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                    belongs_to = cls
                    break

    print(f"Circle is inside rectangle: {belongs_to}")
    if belongs_to == 1:
        return cropped_img1
    elif belongs_to == 2:
        return cropped_img2
    return None


##############################################
# Main Routine
##############################################
def main():
    # 1. Get the verification CAPTCHA image and question values
    verification_img_src, verification_questions, submit_values = get_verification_info()

    # 2. Use multithreading to get anime image URLs from MAL based on verification questions
    anime_images_url = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for anime in verification_questions:
            index, anime_name = anime.split("_+_")
            future = executor.submit(fetch_anime_images_url, anime_name)
            futures[future] = index

        for future in as_completed(futures):
            index = futures[future]
            anime_url = future.result()
            anime_images_url.append((index, anime_url))

    print("Fetched MAL anime image URLs successfully.")

    # 3. Fetch anime images (links + titles) from the URLs concurrently
    anime_images = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for index, url in anime_images_url:
            future = executor.submit(fetch_anime_images, url)
            futures[future] = index

        for future in as_completed(futures):
            index = futures[future]
            image_data = future.result()
            anime_images.extend([(index, img_url) for img_url in image_data])

    print("Fetched anime image links successfully.")

    # 4. Download and decode each anime image concurrently
    result_images = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        
        for index, img_url in anime_images:
            future = executor.submit(fetch_image, img_url)
            futures[future] = index

        for future in as_completed(futures):
            index = futures[future]
            image = future.result()
            result_images.append((index, image))
    print("Downloaded all anime images successfully.")

    # 5. Load the pre-trained YOLO model and run detection on the verification image
    model = YOLO(r"runs\detect\train\weights\best.pt")
    verification_image_resp = request_get_binary(verification_img_src)
    verification_image = Image.open(BytesIO(verification_image_resp)).convert("RGB")
    results = model(verification_image)
    for idx, result in enumerate(results):
        save_filename = f"U2_CAPTCHA_detection_{idx}.jpg"
        result.save(filename=save_filename)
        print(f"Detection result saved to {save_filename}")

    # Process detection results to extract the region of interest
    yolo_detect_img = process_detection_results(results, verification_image)
    if yolo_detect_img is None:
        print("No valid detection region found.")
        return

    # 6. Set up DINO for feature extraction
    device = torch.device('cuda' if torch.cuda.is_available() else "cpu")
    processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
    model_dino = AutoModel.from_pretrained('facebook/dinov2-base').to(device)

    def extract_features(image):
        """Extract image features using DINO."""
        with torch.no_grad():
            inputs = processor(images=image, return_tensors="pt").to(device)
            outputs = model_dino(**inputs)
            # Mean pooling the output features
            image_features = outputs.last_hidden_state.mean(dim=1)
        return image_features

    # Extract features for the detected region from the verification image
    yolo_features = extract_features(yolo_detect_img)

    # 7. Compute cosine similarity between the verification region and each downloaded anime image
    cos = torch.nn.CosineSimilarity(dim=0)

    max_sim_by_index = {}

    for index, image in result_images:
        features = extract_features(image)
        sim = cos(features[0], yolo_features[0]).item()
        sim = (sim + 1) / 2  

        if index not in max_sim_by_index or sim > max_sim_by_index[index]:
            max_sim_by_index[index] = sim


    sorted_indexs = sorted(max_sim_by_index.items(), key=lambda x: x[1], reverse=True)
    index_mapping = {index: anime for submit_value in submit_values for index, anime in [submit_value.split("_+_")]}

    if not sorted_indexs or sorted_indexs[0][1] < 0.90:
        print("⚠️ Warning: Maximum similarity is below 90%, results may be unreliable.")

    print("\n\n=====================================================")

    for index, sim in sorted_indexs:
        anime_name = index_mapping.get(index, index)
        print(f"{sim*100:.2f}% {anime_name}")

if __name__ == "__main__":
    main()