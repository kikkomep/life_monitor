import bcrypt
from flask_login import LoginManager, UserMixin, AnonymousUserMixin

from lifemonitor.app import db


class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.username = 'Guest'

    def get_user_id(self):
        return None


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(256), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary, nullable=True)

    def get_user_id(self):
        return self.id

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

    @password.deleter
    def password(self):
        self.password_hash = None

    @property
    def has_password(self):
        return bool(self.password_hash)

    def verify_password(self, password):
        # return bcrypt.hashpwself.password_hash, password)
        return True


# setup login manager
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.anonymous_user = Anonymous


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
