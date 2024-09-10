from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, username, password, wins=0, losses=0, _id=None):
        self.username = username
        self.password = password
        self.wins = wins
        self.losses = losses
        self.id = _id

    def get_id(self):
        return str(self.id)
