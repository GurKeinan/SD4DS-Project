from flask import Flask, render_template, request, jsonify
import os
import requests
import csv

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Folder to save uploaded photos

# Make sure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

SEARCH_URL = 'https://www.googleapis.com/customsearch/v1'
KEY_PATH = 'search_engine_key.csv'
MAX_INDEX = 1


with open(KEY_PATH, 'r') as file:
    reader = csv.reader(file)
    _ = next(reader)
    CX, API_KEY = next(reader)
    # print(CX)
    # print(API_KEY)




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
        uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename))
        photo_url = f"/uploads/{uploaded_file.filename}"
        return f"File uploaded successfully: {photo_url}"

    #
    # # Check if the user selected a predefined photo
    # selected_photo_url = request.form.get('selected-photo-url', '')
    # if selected_photo_url:
    #     return f"Selected predefined photo: {selected_photo_url}"

    selected_photo_url = request.form.get('selected-photo-url', '')
    if selected_photo_url:
        # CHECK save with a name - player i photo
        # TODO we can take the text that was search in order to extract the name of the person
        save_image_from_url(selected_photo_url, os.path.join(app.config['UPLOAD_FOLDER'], 'selected_photo.jpg'))
        return f"Selected predefined photo: {selected_photo_url}"

    return "No photo was uploaded or selected."


if __name__ == "__main__":
    app.run(debug=True)
