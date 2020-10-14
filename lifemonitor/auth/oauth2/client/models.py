from __future__ import annotations

from typing import List
from datetime import datetime
from sqlalchemy import DateTime
from urllib.parse import urljoin
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import NoResultFound
from lifemonitor.db import db
from importlib import import_module
from lifemonitor.auth.models import User
from lifemonitor.common import EntityNotFoundException, LifeMonitorException


class OAuthIdentityNotFoundException(EntityNotFoundException):
    def __init__(self, entity_id=None) -> None:
        super().__init__(entity_class=self.__class__)
        self.entity_id = entity_id


class OAuthUserProfile:

    def __init__(self, sub=None, name=None, email=None, mbox_sha1sum=None,
                 preferred_username=None, profile=None, picture=None, website=None) -> None:
        self.sub = sub
        self.name = name
        self.email = email
        self.mbox_sha1sum = mbox_sha1sum
        self.preferred_username = preferred_username
        self.profile = profile
        self.picture = picture
        self.website = website

    def to_dict(self):
        res = {}
        for k in ['sub', 'name', 'email', 'mbox_sha1sum', 'preferred_username', 'profile', 'picture', 'website']:
            res[k] = getattr(self, k)
        return res

    @staticmethod
    def from_dict(data: dict):
        profile = OAuthUserProfile()
        for k, v, in data.items():
            setattr(profile, k, v)
        return profile


class OAuthIdentity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    provider_user_id = db.Column(db.String(256), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("oauth2_identity_provider.id"), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    token = db.Column(JSONB, nullable=True)
    user_info = db.Column(JSONB, nullable=True)
    provider = db.relationship("OAuth2IdentityProvider", uselist=False, back_populates="identities")
    user = db.relationship(
        User,
        # This `backref` thing sets up an `oauth` property on the User model,
        # which is a dictionary of OAuth models associated with that user,
        # where the dictionary key is the OAuth provider name.
        backref=db.backref(
            "oauth_identity",
            collection_class=attribute_mapped_collection("provider.name"),
            cascade="all, delete-orphan",
        ),
    )

    __table_args__ = (db.UniqueConstraint("provider_id", "provider_user_id"),)
    __tablename__ = "oauth2_identity"

    def __init__(self, provider, user_info, provider_user_id, token):
        self.provider = provider
        self.provider_user_id = provider_user_id
        self.user_info = user_info
        self.token = token

    @property
    def username(self):
        return f"{self.provider.name}_{self.user_info['sub']}"

    def __repr__(self):
        parts = []
        parts.append(self.__class__.__name__)
        if self.id:
            parts.append("id={}".format(self.id))
        if self.provider:
            parts.append('provider="{}"'.format(self.provider))
        return "<{}>".format(" ".join(parts))

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def find_by_user_id(user_id, provider_name) -> OAuthIdentity:
        try:
            return OAuthIdentity.query\
                .filter(OAuthIdentity.provider.has(name=provider_name))\
                .filter_by(user_id=user_id).one()
        except NoResultFound:
            raise OAuthIdentityNotFoundException(f"{user_id}_{provider_name}")

    @staticmethod
    def find_by_provider_user_id(provider_user_id, provider_name) -> OAuthIdentity:
        try:
            return OAuthIdentity.query\
                .filter(OAuthIdentity.provider.has(name=provider_name))\
                .filter_by(provider_user_id=provider_user_id).one()
        except NoResultFound:
            raise OAuthIdentityNotFoundException(f"{provider_name}_{provider_user_id}")

    @classmethod
    def all(cls):
        return cls.query.all()


class OAuth2IdentityProvider(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    _type = db.Column("type", db.String, nullable=False)
    name = db.Column(db.String, nullable=False, unique=True)
    client_id = db.Column(db.String, nullable=False)
    client_secret = db.Column(db.String, nullable=False)
    client_kwargs = db.Column(JSONB, nullable=True)
    _api_base_url = db.Column("api_base_url", db.String, nullable=False)
    _authorize_url = db.Column("authorize_url", db.String, nullable=False)
    authorize_params = db.Column(JSONB, nullable=True)
    _access_token_url = db.Column("access_token_url", db.String, nullable=False)
    access_token_params = db.Column(JSONB, nullable=True)
    userinfo_endpoint = db.Column(db.String, nullable=False)
    identities = db.relationship("OAuthIdentity",
                                 back_populates="provider", cascade="all, delete")

    __tablename__ = "oauth2_identity_provider"
    __mapper_args__ = {
        'polymorphic_on': _type,
        'polymorphic_identity': 'oauth2_identity_provider'
    }

    def __init__(self, name,
                 client_id, client_secret,
                 api_base_url, authorize_url, access_token_url, userinfo_endpoint,
                 client_kwargs=None,
                 authorize_params=None,
                 access_token_params=None):
        self.name = name
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_base_url = api_base_url
        self.client_kwargs = client_kwargs
        self.authorize_url = authorize_url
        self.access_token_url = access_token_url
        self.access_token_params = access_token_params
        self.userinfo_endpoint = urljoin(api_base_url, userinfo_endpoint)

    @property
    def type(self):
        return self._type

    @hybrid_property
    def api_base_url(self):
        return self._api_base_url

    @api_base_url.setter
    def api_base_url(self, api_base_url):
        assert api_base_url and len(api_base_url) > 0, "URL cannot be empty"
        self._api_base_url = api_base_url

    @hybrid_property
    def authorize_url(self):
        return self._authorize_url

    @authorize_url.setter
    def authorize_url(self, authorize_url):
        assert authorize_url and len(authorize_url) > 0, "URL cannot be empty"
        self._authorize_url = urljoin(self.api_base_url, authorize_url)

    @hybrid_property
    def access_token_url(self):
        return self._access_token_url

    @access_token_url.setter
    def access_token_url(self, token_url):
        assert token_url and len(token_url) > 0, "URL cannot be empty"
        self._access_token_url = urljoin(self.api_base_url, token_url)

    @property
    def oauth_config(self):
        return {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'client_kwargs': self.client_kwargs,
            'api_base_url': self.api_base_url,
            'authorize_url': self.authorize_url,
            'authorize_params': self.authorize_params,
            'access_token_url': self.access_token_url,
            'access_token_params': self.access_token_params,
            'userinfo_endpoint': self.userinfo_endpoint,
            'userinfo_compliance_fix': self.normalize_userinfo,
        }

    def normalize_userinfo(self, client, data):
        m = f"lifemonitor.auth.oauth2.client.providers.{self.type}"
        try:
            mod = import_module(m)
            return getattr(mod, "normalize_userinfo")(client, data)
        except ModuleNotFoundError:
            raise LifeMonitorException(f"ModuleNotFoundError: Unable to load module {m}")
        except AttributeError:
            raise LifeMonitorException(f"Unable to create an instance of WorkflowRegistryClient from module {m}")

    def find_identity_by_provider_user_id(self, provider_user_id):
        try:
            return OAuthIdentity.query.with_parent(self)\
                .filter_by(provider_user_id=provider_user_id).one()
        except NoResultFound:
            raise OAuthIdentityNotFoundException(f"{provider_user_id}@{self}")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find(cls, name) -> OAuth2IdentityProvider:
        return cls.query.filter(cls.name == name).one()

    @classmethod
    def all(cls) -> List(OAuth2IdentityProvider):
        return cls.query.all()
