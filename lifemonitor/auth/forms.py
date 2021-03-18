import logging

from flask_wtf import FlaskForm
from sqlalchemy.exc import IntegrityError
from wtforms import HiddenField, PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Optional

from .models import User, db

# Set the module level logger
logger = logging.getLogger(__name__)


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    provider = HiddenField("Provider", validators=[Optional()])

    def get_user(self):
        user = User.query.filter_by(username=self.username.data).first()
        if not user:
            self.username.errors.append("Username not found")
            return None
        if not user.verify_password(self.password.data):
            self.password.errors.append("Invalid password")
            return None
        return user


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            EqualTo("repeat_password", message="Passwords must match"),
        ],
    )
    repeat_password = PasswordField("Repeat Password")
    identity = HiddenField("identity")

    def create_user(self, identity=None):
        user = User(username=self.username.data)
        if identity:
            identity.user = user
        else:
            user.password = self.password.data
        db.session.add(user)
        try:
            db.session.commit()
            return user
        except IntegrityError:
            self.username.errors.append("This username is already taken")
            db.session.rollback()
            return None

    def validate(self, extra_validators=None):
        # if the current user has an external OAuth2 identity
        # then we do not validate the password field (which is optional)
        logger.debug("OAuth identity: %r (%r)", self.identity.raw_data, not self.identity.data)
        if self.identity.data:
            return self.username.validate(self)
        return super().validate(extra_validators=extra_validators)


class SetPasswordForm(FlaskForm):
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            EqualTo("repeat_password", message="Passwords must match"),
        ],
    )
    repeat_password = PasswordField("Repeat Password")
