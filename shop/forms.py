from flask_wtf import FlaskForm
from wtforms.validators import InputRequired, Email
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.fields import TextField, TextAreaField, IntegerField, BooleanField

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

class CancelSubscriptionForm(FlaskForm):
    email = TextField('Email', [Email()])

class ProductForm(FlaskForm):
    name = TextField('Name', [InputRequired()])
    desc = TextAreaField('Description', [InputRequired()])
    price = IntegerField('Price (cents)', [InputRequired()])
    published = BooleanField('Published')

class SKUForm(FlaskForm):
    name = TextField('Name', [InputRequired()])
    stock = IntegerField('Stock', [InputRequired()])

class ImageForm(FlaskForm):
    file = FileField('Image', [FileRequired(),
                               FileAllowed(ALLOWED_EXTENSIONS, 'Images only')])

