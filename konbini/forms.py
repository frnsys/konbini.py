from flask_wtf import FlaskForm
from country_list import countries_for_language
from wtforms.validators import Email, Length, InputRequired
from wtforms.fields import TextField, FormField, SelectField, HiddenField
from wtforms.fields.html5 import EmailField

countries = countries_for_language('en')

class CancelSubscriptionForm(FlaskForm):
    email = TextField('Email', [Email()])

class AddressForm(FlaskForm):
    line1 = TextField('Address', [InputRequired()])
    line2 = TextField('Address 2')
    city = TextField('City', [InputRequired()])
    state = TextField('State', [Length(max=2)]) # Not always used in int'l addresses. Shipbob requires 2 character state abbreviations.
    postal_code = TextField('Zipcode', [InputRequired()])
    country = SelectField('Country', [InputRequired()], choices=countries, default='US')

class ShippingForm(FlaskForm):
    name = TextField('Name', [InputRequired()])
    email = EmailField('Email', [InputRequired(), Email()])
    address = FormField(AddressForm)

class EmailForm(FlaskForm):
    email = EmailField('Email', [InputRequired(), Email()])

class AddToCartForm(FlaskForm):
    name = HiddenField('Name')
    sku = HiddenField('Sku')
    product = HiddenField('Product')
