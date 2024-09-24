import random
import requests
import string
import os
import re
import base64
from PIL import Image
from flask import url_for
from gradio_client import handle_file
from . import face_swap_client, app


MAX_INDEX = 1
SEARCH_URL = 'https://www.googleapis.com/customsearch/v1'


def generate_game_code(length=6):
    """Generates a random game code."""
    letters_and_digits = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(length))


def fetch_photos(query, prefix='', suffix='', start_index=1):
    q = query
    if prefix:
        q = prefix + ' ' + q
    if suffix:
        q = q + ' ' + suffix
    params = {
        'key': os.environ.get('SEARCH_ENGINE_API_KEY'),
        'cx': os.environ.get('CX'),
        'q': q,
        'searchType': 'image',
        'start': start_index,  # Starting index for pagination
        'num': 10,  # Number of results per page (up to 10)
    }

    response = requests.get(SEARCH_URL, params=params)

    data = response.json()
    links = [item['link'] for item in data.get('items', [])]
    alts = [item.get('title', '') for item in data.get('items', [])]
    photos_sizes = [(item['image']['height'], item['image']['width']) for item in data.get('items', [])]
    # Print image URLs from the first page
    return links, alts, photos_sizes


def fetch_photos_extended(query, amount=10, check_size=False, prefix='', suffix='portrait'):
    current_amount = 0
    start_index = 1
    photo_urls = []
    photos_alts = []
    # prev_len = 0
    while current_amount < amount and start_index <= MAX_INDEX:
        # print(start_index, current_amount)
        links, alts, photos_sizes = fetch_photos(query, prefix, suffix, start_index)
        if len(links) == 0:
            print('No photos found in index', start_index)
            break
        for i in range(len(links)):
            if current_amount >= amount:
                break

            if (photos_sizes[i][0] >= photos_sizes[i][1] or not check_size) and links[i] not in photo_urls:
                photo_urls.append(links[i])
                photos_alts.append(alts[i])
                current_amount += 1
        # if prev_len == current_amount or current_amount >= amount:
        #     break
        start_index += 1
        # prev_len = current_amount
    if current_amount < amount:
        print('Not enough photos found')
    return [{'url': photo_urls[i], 'alt': photos_alts[i]} for i in range(len(photo_urls))]


def save_image_from_url(url, file_name):
    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Open a file in binary write mode and save the image
        with open(file_name, 'wb') as image_file:
            image_file.write(response.content)
        print(f"Image successfully saved as {file_name}")
    else:
        print("Failed to retrieve the image.")


def save_base64_image(base64_string, filename):
    cleaned_string = re.sub(r'\s+', '', base64_string)
    padded_base64_string = cleaned_string + "=" * ((4 - len(cleaned_string) % 4) % 4)
    image_data = base64.b64decode(padded_base64_string)
    with open(filename, "wb") as file:
        file.write(image_data)


def merge_images(image1_path, image2_path, output_path):
    # Flip a coin to decide which image is the target and which is the source
    coin_flip = random.choice([True, False])
    if coin_flip:
        target = image1_path
        source = image2_path
    else:
        target = image2_path
        source = image1_path

    # Perform the face swap
    result = face_swap_client.predict(
        target=handle_file(target),
        source=handle_file(source),
        slider=100,
        adv_slider=100,
        settings=["Adversarial Defense"],
        api_name="/run_inference"
    )

    # Temporary path to the result (which is in .webp format)
    temp_result_path = result  # Path like "/private/var/.../image.webp"

    # Open the .webp image using Pillow
    image = Image.open(temp_result_path)

    # Ensure the outputs folder exists
    # outputs_dir = os.path.join(app.config['OUTPUT_FOLDER'], 'outputs')
    # if not os.path.exists(outputs_dir):
    #     os.makedirs(outputs_dir)

    # Save the image as .jpeg in the outputs folder
    jpeg_save_path = os.path.join(app.config['OUTPUT_FOLDER'], output_path)
    image.save(jpeg_save_path, "JPEG")

    print(f"Image saved as {jpeg_save_path}")

    # Return the URL for the saved image
    return url_for('static', filename=f'outputs/{output_path}')
