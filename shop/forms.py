from flask_wtf import FlaskForm
from wtforms.fields import TextField
from wtforms.validators import Email

class CancelSubscriptionForm(FlaskForm):
    email = TextField('Email', [Email()])
