from flask_mail import Message
from flask import current_app, render_template

def send_email(tos, subject, template, reply_to=None, bcc=None, **kwargs):
    reply_to = reply_to or current_app.config['MAIL_REPLY_TO']
    msg = Message(subject,
                body=render_template('shop/email/{}.txt'.format(template), **kwargs),
                html=render_template('shop/email/{}.html'.format(template), **kwargs),
                recipients=tos,
                reply_to=reply_to,
                bcc=bcc)
    mail = current_app.extensions.get('mail')
    mail.send(msg)

def check_state(state):
    abbreviation_to_name = {
        "AK": "Alaska",
        "AL": "Alabama",
        "AR": "Arkansas",
        "AZ": "Arizona",
        "CA": "California",
        "CO": "Colorado",
        "CT": "Connecticut",
        "DE": "Delaware",
        "FL": "Florida",
        "GA": "Georgia",
        "HI": "Hawaii",
        "IA": "Iowa",
        "ID": "Idaho",
        "IL": "Illinois",
        "IN": "Indiana",
        "KS": "Kansas",
        "KY": "Kentucky",
        "LA": "Louisiana",
        "MA": "Massachusetts",
        "MD": "Maryland",
        "ME": "Maine",
        "MI": "Michigan",
        "MN": "Minnesota",
        "MO": "Missouri",
        "MS": "Mississippi",
        "MT": "Montana",
        "NC": "North Carolina",
        "ND": "North Dakota",
        "NE": "Nebraska",
        "NH": "New Hampshire",
        "NJ": "New Jersey",
        "NM": "New Mexico",
        "NV": "Nevada",
        "NY": "New York",
        "OH": "Ohio",
        "OK": "Oklahoma",
        "OR": "Oregon",
        "PA": "Pennsylvania",
        "RI": "Rhode Island",
        "SC": "South Carolina",
        "SD": "South Dakota",
        "TN": "Tennessee",
        "TX": "Texas",
        "UT": "Utah",
        "VA": "Virginia",
        "VT": "Vermont",
        "WA": "Washington",
        "WI": "Wisconsin",
        "WV": "West Virginia",
        "WY": "Wyoming",
        "DC": "District of Columbia",
        "AS": "American Samoa",
        "GU": "Guam GU",
        "MP": "Northern Mariana Islands",
        "PR": "Puerto Rico PR",
        "VI": "U.S. Virgin Islands",
    }

    if state.upper() in abbreviation_to_name.keys():
        return abbreviation_to_name[state.upper()]
    else:
        return state
