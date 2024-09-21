import requests
from . import app, mongo, bcrypt, login_manager



@app.route('/api/status')
def api_status():
    response = requests.get('http://face-merge-image-classification-api:6000/status')
    return "The response from our API server is:" + response.text, response.status_code, response.headers.items()