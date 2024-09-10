import requests
import os # use for getting environment variables

MAX_INDEX = 1
SEARCH_URL = 'https://www.googleapis.com/customsearch/v1'


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
        'imgSize': 'large'  # CHECK Filter by image size
    }

    response = requests.get(SEARCH_URL, params=params)

    data = response.json()
    links = [item['link'] for item in data.get('items', [])]
    alts = [item.get('title', '') for item in data.get('items', [])]
    photos_sizes = [(item['image']['height'], item['image']['width']) for item in data.get('items', [])]
    # Print image URLs from the first page  CHECK more pages
    return links, alts, photos_sizes


def fetch_photos_extended(query, amount=10, check_size=False, prefix='', suffix='portrait'):  # CHECK portrait of
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