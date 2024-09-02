from flask import Flask
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MONGO_URI'] = 'mongodb://face-merge-mongodb:27017/face_merge_db'

mongo = PyMongo(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

waiting_users_collection = mongo.db.waiting_users  # New collection for waiting users

from app import routes

@app.context_processor
def inject_user():
    return dict(user=current_user)

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5001)