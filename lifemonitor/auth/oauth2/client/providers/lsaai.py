# Copyright (c) 2020-2024 CRS4
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging

from flask import current_app
from lifemonitor.exceptions import OAuthAuthorizationException
from lifemonitor.auth.oauth2.client.models import OAuthIdentity

# Config a module level logger
logger = logging.getLogger(__name__)


def normalize_userinfo(client, data):
    info = {}
    try:
        info["sub"] = data['sub']
    except KeyError:
        raise OAuthAuthorizationException(title="Unable to get user data",
                                          description="the LS ID is required")
    for key in ['name', 'email', 'preferred_username']:
        info[key] = data.get(key, None)
        if info[key] is None:
            logger.warning("User %r has no %r", info["sub"], key)

    return info


class LsAAI:
    name = 'LifeScience RI'
    client_name = 'lsaai'
    oauth_config = {
        'client_id': current_app.config.get('LSAAI_CLIENT_ID', None),
        'client_secret': current_app.config.get('LSAAI_CLIENT_SECRET', None),
        'client_name': client_name,
        'uri': 'https://login.aai.lifescience-ri.eu',
        'api_base_url': 'https://login.aai.lifescience-ri.eu',
        'access_token_url': 'https://login.aai.lifescience-ri.eu/oidc/token',
        'authorize_url': 'https://login.aai.lifescience-ri.eu/oidc/authorize',
        'client_kwargs': {'scope': 'openid profile email'},
        'userinfo_endpoint': 'https://login.aai.lifescience-ri.eu/oidc/userinfo',
        'userinfo_compliance_fix': normalize_userinfo,
        'user_profile_html': 'https://profile.aai.lifescience-ri.eu/profile',
        'server_metadata_url': 'https://login.aai.lifescience-ri.eu/oidc/.well-known/openid-configuration'
    }

    def __repr__(self) -> str:
        return "LSAAI Provider"

    @classmethod
    def get_user_profile_page(cls, user_identity: OAuthIdentity):
        logger.warning("user: %r", user_identity)
        # the user profile page can be retrieved without user_provider_id
        return cls.oauth_config['user_profile_html']

    @staticmethod
    def normalize_userinfo(client, data):
        return normalize_userinfo(client, data)
