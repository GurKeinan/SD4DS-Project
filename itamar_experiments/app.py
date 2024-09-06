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
MAX_INDEX = 10


def fetch_photos(query, prefix='portrait of', start_index=1):  # CHECK portrait of
    params = {
        'key': API_KEY,
        'cx': CX,
        'q': prefix + ' ' + query if (prefix is not None and len(prefix) > 0) else query,
        'searchType': 'image',
        'start': start_index,  # Starting index for pagination
        'num': 10  # Number of results per page (up to 10)
    }

    response = requests.get(SEARCH_URL, params=params)

    data = response.json()
    res = [(item['link'], item['title']) for item in data.get('items', [])]
    # Print image URLs from the first page  CHECK more pages
    return res


def fetch_photos_extended(query, amount=10, prefix='portrait of'):  # CHECK portrait of
    current_amount = 0
    start_index = 1
    photo_urls = []
    prev_len = -1
    while current_amount < amount and start_index < MAX_INDEX:
        photo_urls += fetch_photos(query, prefix, start_index)
        photo_urls = list(set(photo_urls))
        current_amount = len(photo_urls)
        if prev_len == current_amount:
            break
        start_index += 1
        prev_len = current_amount
    return photo_urls[:amount]


@app.route("/")
def index():
    return render_template("upload.html")


# Route to search for photos by text
@app.route("/search_photos", methods=["POST"])
def search_photos():
    data = request.get_json()
    query = data.get('query', '')

    # Call the function to get the URLs based on the text query
    photo_urls = fetch_photos_extended(query, 20)

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
