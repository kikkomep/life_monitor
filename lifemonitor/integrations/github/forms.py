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

import logging

import json

from flask_wtf import FlaskForm
from lifemonitor.auth.models import User
from wtforms import BooleanField, StringField, HiddenField
from wtforms.validators import AnyOf
from lifemonitor.api import models

from .settings import GithubUserSettings

# Set the module level logger
logger = logging.getLogger(__name__)


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

    registries = HiddenField(
        "registries",
        description="")

    available_registries = models.WorkflowRegistry.all()

    def update_model(self, user: User, skip_periodic_builds: bool = False) -> GithubUserSettings:
        assert user and not user.is_anonymous, user
        settings = GithubUserSettings(user) \
            if not user.github_settings else user.github_settings
        settings.all_branches = self.all_branches.data
        settings.all_tags = self.all_tags.data
        settings.check_issues = self.check_issues.data
        settings.enable_integration = self.enable_integration.data
        if not skip_periodic_builds:
            settings.periodic_builds = self.periodic_builds.data
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
            "registries": self.registries.data
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

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
        form.enable_integration.data = data.get("enable_integration")
        form.registries.data = data.get("registries")
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
        form.enable_integration.data = settings.enable_integration
        return form
