from flask_wtf import FlaskForm
from country_list import countries_for_language
from wtforms.validators import Email, InputRequired
from wtforms.fields import TextField, FormField, SelectField

countries = countries_for_language('en')

class CancelSubscriptionForm(FlaskForm):
    email = TextField('Email', [Email()])

class AddressForm(FlaskForm):
    line1 = TextField('Address', [InputRequired()])
    line2 = TextField('Address 2')
    city = TextField('City', [InputRequired()])
    state = TextField('State') # Not always used in int'l addresses
    postal_code = TextField('Zipcode', [InputRequired()])
    country = SelectField('Country', [InputRequired()], choices=countries, default='US')

class ShippingForm(FlaskForm):
    name = TextField('Name', [InputRequired()])
    address = FormField(AddressForm)
