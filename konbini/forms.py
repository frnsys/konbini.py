from flask_wtf import FlaskForm
from country_list import countries_for_language
from wtforms.validators import Email, Length, InputRequired
from wtforms.fields import StringField, FormField, SelectField, HiddenField, EmailField

countries = countries_for_language('en')

class CancelSubscriptionForm(FlaskForm):
    email = StringField('Email', [Email()])

class AddressForm(FlaskForm):
    line1 = StringField('Address', [InputRequired()])
    line2 = StringField('Address 2')
    city = StringField('City', [InputRequired()])
    state = StringField('State', [Length(max=2)]) # Not always used in int'l addresses. Shipbob requires 2 character state abbreviations.
    postal_code = StringField('Zipcode', [InputRequired()])
    country = SelectField('Country', [InputRequired()], choices=countries, default='US')

class ShippingForm(FlaskForm):
    name = StringField('Name', [InputRequired()])
    email = EmailField('Email', [InputRequired(), Email()])
    address = FormField(AddressForm)

class EmailForm(FlaskForm):
    email = EmailField('Email', [InputRequired(), Email()])

class AddToCartForm(FlaskForm):
    name = HiddenField('Name')
    sku = HiddenField('Sku')
    product = HiddenField('Product')
