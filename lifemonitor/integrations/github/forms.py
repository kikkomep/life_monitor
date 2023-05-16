# Copyright (c) 2020-2022 CRS4
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


from __future__ import annotations

import json
import logging

from flask import session
from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, StringField
from wtforms.validators import AnyOf, DataRequired, ValidationError

from lifemonitor.api import models
from lifemonitor.auth.models import User

from .settings import GithubUserSettings

# Set the module level logger
logger = logging.getLogger(__name__)


class GithubIntegrationForm(FlaskForm):

    enable_integration = BooleanField(
        "enable_integration",
        validators=[AnyOf([True, False])]
    )

    def update_model(self, user: User) -> GithubUserSettings:
        assert user and not user.is_anonymous, user
        settings = GithubUserSettings(user) \
            if not user.github_settings else user.github_settings
        settings.enable_integration = self.enable_integration.data
        logger.error("Settings: %r", settings)
        return settings

    @classmethod
    def from_model(cls, user: User) -> GithubSettingsForm:
        if user.is_anonymous:
            return None
        settings = GithubUserSettings(user) \
            if not user.github_settings else user.github_settings
        form = cls()
        form.enable_integration.data = settings.enable_integration
        return form


def test_validatable_field(form, field):
    try:
        field.data = field.data.strip()
        if field.data:
            valid = GithubUserSettings.is_periodic_builds_interval_valid(field.data)
            if not valid:
                raise ValueError("Invalid periodic builds interval")
        return True
    except ValueError as e:
        raise ValidationError(e)


class GithubSettingsForm(FlaskForm):
    branches = StringField(
        "branches",
        description="List of comma-separated branches (e.g., master, develop, feature/123)")
    tags = StringField(
        "tags",
        description="List of comma-separated tags (e.g., v*, v*.*.*, release-v*)")
    all_branches = BooleanField(
        "all_branches",
        validators=[AnyOf([True, False])]
    )
    all_tags = BooleanField(
        "all_tags",
        validators=[AnyOf([True, False])]
    )
    check_issues = BooleanField(
        "check_issues",
        validators=[AnyOf([True, False])]
    )

    enable_integration = BooleanField(
        "enable_integration",
        validators=[AnyOf([True, False])]
    )

    periodic_builds = BooleanField(
        "periodic_builds",
        validators=[AnyOf([True, False])]
    )

    periodic_builds_wo_ghapp = BooleanField(
        "periodic_builds_wo_ghapp",
        validators=[AnyOf([True, False])]
    )

    periodic_builds_interval = StringField(
        "periodic_builds_interval",
        validators=[DataRequired(), test_validatable_field],
        default="@weekly",
    )

    registries = HiddenField(
        "registries",
        description="")

    available_registries = models.WorkflowRegistry.all()

    def invalid_csrf_token(self) -> bool:
        t = getattr(self, 'csrf_token', None)
        if t and len(t.errors) > 0:
            return True
        return False

    def update_model(self, user: User, skip_periodic_builds_wo_ghapp: bool = False) -> GithubUserSettings:
        assert user and not user.is_anonymous, user
        settings = GithubUserSettings(user) \
            if not user.github_settings else user.github_settings
        settings.all_branches = self.all_branches.data
        settings.all_tags = self.all_tags.data
        settings.check_issues = self.check_issues.data
        settings.enable_integration = self.enable_integration.data
        settings.periodic_builds = self.periodic_builds.data
        if not skip_periodic_builds_wo_ghapp:
            settings.periodic_builds_wo_ghapp = self.periodic_builds_wo_ghapp.data
        settings.periodic_builds_interval = self.periodic_builds_interval.data
        settings.branches = [_.strip() for _ in self.branches.data.split(',')] if self.branches.data else []
        settings.tags = [_.strip() for _ in self.tags.data.split(',')] if self.tags.data else []
        logger.error("Settings: %r", settings)
        return settings

    def to_dict(self) -> str:
        return {
            "branches": self.branches.data,
            "tags": self.tags.data,
            "all_branches": self.all_branches.data,
            "all_tags": self.all_tags.data,
            "check_issues": self.check_issues.data,
            "enable_integration": self.enable_integration.data,
            "periodic_builds": self.periodic_builds.data,
            "periodic_builds_wo_ghapp": self.periodic_builds_wo_ghapp.data,
            "periodic_builds_interval": self.periodic_builds_interval.data,
            "registries": self.registries.data,
            "csrf_token": self.csrf_token.data,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_session(self):
        session['lm-github-settings-form'] = self.to_json()

    @classmethod
    def from_json(cls, data: str) -> GithubSettingsForm:
        return cls.from_dict(json.loads(data))

    @classmethod
    def from_dict(cls, data: dict) -> GithubSettingsForm:
        form = cls()
        form.all_branches.data = data.get("all_branches")
        form.all_tags.data = data.get("all_tags")
        form.branches.data = data.get("branches")
        form.tags.data = data.get("tags")
        form.check_issues.data = data.get("check_issues")
        form.periodic_builds.data = data.get("periodic_builds")
        form.periodic_builds_wo_ghapp.data = data.get("periodic_builds_wo_ghapp")
        form.enable_integration.data = data.get("enable_integration")
        form.registries.data = data.get("registries")
        form.periodic_builds_interval.data = data.get("periodic_builds_interval")
        csrf_token = getattr(form, "csrf_token", None)
        if csrf_token:
            csrf_token.data = data.get("csrf_token")
        return form

    @classmethod
    def from_model(cls, user: User) -> GithubSettingsForm:
        if user.is_anonymous:
            return None
        settings = GithubUserSettings(user) \
            if not user.github_settings else user.github_settings
        form = cls()
        form.all_branches.data = settings.all_branches
        form.all_tags.data = settings.all_tags
        form.branches.data = ', '.join(settings.branches)
        form.tags.data = ', '.join(settings.tags)
        form.check_issues.data = settings.check_issues
        form.periodic_builds.data = settings.periodic_builds
        form.periodic_builds_wo_ghapp.data = settings.periodic_builds_wo_ghapp
        form.enable_integration.data = settings.enable_integration
        form.periodic_builds_interval.data = settings.periodic_builds_interval
        return form

    @classmethod
    def from_session(cls) -> GithubSettingsForm:
        data = session.pop("lm-github-settings-form", None)
        logger.warning("Session data: %r", data)
        form = None
        if data:
            form = cls.from_json(data)
            if form:
                form.validate()
        return form
