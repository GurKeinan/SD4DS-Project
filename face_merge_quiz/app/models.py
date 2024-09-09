from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, username, password, wins=0, losses=0, _id=None):
        self.id = _id
        self.username = username
        self.password = password  # This will be the hashed password
        self.wins = wins
        self.losses = losses
