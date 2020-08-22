from __future__ import annotations

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

    def __init__(self, username=None) -> None:
        super().__init__()
        self.username = username

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

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def find_by_username(username):
        return User.query.filter(User.username == username).first()


# setup login manager
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.anonymous_user = Anonymous


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class ApiKey(db.Model):
    SCOPES = ["read", "write"]

    key = db.Column(db.String, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = db.relationship(
        'User',
        backref=db.backref("api_keys", cascade="all, delete-orphan"),
    )
    scope = db.Column(db.String, nullable=False)

    def __init__(self, key=None, user=None, scope=None) -> None:
        super().__init__()
        self.key = key
        self.user = user
        self.scope = scope or ""

    def __repr__(self) -> str:
        return "ApiKey {} (scope: {})".format(self.key, self.scope)

    def set_scope(self, scope):
        if scope:
            for s in scope.split(" "):
                if s not in self.SCOPES:
                    raise ValueError("Scope '%r' not valid".format(s))
                self.scope = "{} {}".format(self.scope, s)

    def check_scopes(self, scopes: list or str):
        if isinstance(scopes, str):
            scopes = scopes.split(" ")
        supported_scopes = self.scope.split(" ")
        for scope in scopes:
            if scope not in supported_scopes:
                return False
        return True

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find(cls, api_key) -> ApiKey:
        return cls.query.filter(ApiKey.key == api_key).first()
