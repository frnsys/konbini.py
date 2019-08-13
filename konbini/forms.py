from flask_wtf import FlaskForm
from wtforms.fields import TextField, FormField
from wtforms.validators import Email, InputRequired

class CancelSubscriptionForm(FlaskForm):
    email = TextField('Email', [Email()])

class AddressForm(FlaskForm):
    line1 = TextField('Address', [InputRequired()])
    line2 = TextField('Address 2')
    city = TextField('City', [InputRequired()])
    state = TextField('State', [InputRequired()])
    # country = TextField('Country', [InputRequired()])
    postal_code = TextField('Zipcode', [InputRequired()])

class CheckoutForm(FlaskForm):
    name = TextField('Name', [InputRequired()])
    address = FormField(AddressForm)
