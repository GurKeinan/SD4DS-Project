from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Folder to save uploaded photos

# Make sure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

API_KEY = 'AIzaSyB3Hi3ca28V8fXz8ZsXG6_5uB2UGY1_MJw'
CX = '83884353925084eaa'

SEARCH_URL = 'https://www.googleapis.com/customsearch/v1'
MAX_INDEX = 1


def fetch_photos(query, prefix='', suffix='', start_index=1):
    q = query
    if prefix:
        q = prefix + ' ' + q
    if suffix:
        q = q + ' ' + suffix
    params = {
        'key': API_KEY,
        'cx': CX,
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


@app.route("/")
def index():
    return render_template("upload.html")


# Route to search for photos by text
@app.route("/search_photos", methods=["POST"])
def search_photos():
    data = request.get_json()
    query = data.get('query', '')

    # Call the function to get the URLs based on the text query
    photo_urls = fetch_photos_extended(query, amount=10)
    # for photo in photo_urls:
    #     print(photo['url'])
    #     print(photo['alt'])
    #     print('\n')

    # Return the URLs as a JSON response
    return jsonify({"photos": photo_urls})


# Route to handle the form submission (upload or predefined photo selection)
@app.route("/", methods=["POST"])
def handle_form_submission():
    # Check if the user uploaded a file
    if 'file' in request.files and request.files['file'].filename != '':
        uploaded_file = request.files['file']
        # Process the uploaded file (e.g., save it to the server)
        uploaded_file.save(os.path.join('uploads', uploaded_file.filename))
        photo_url = f"/uploads/{uploaded_file.filename}"
        return f"File uploaded successfully: {photo_url}"

    # Check if the user selected a predefined photo
    selected_photo_url = request.form.get('selected-photo-url', '')
    if selected_photo_url:
        return f"Selected predefined photo: {selected_photo_url}"

    return "No photo was uploaded or selected."


if __name__ == "__main__":
    app.run(debug=True)
