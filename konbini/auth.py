from . import core
from functools import wraps
from .forms import EmailForm
from .util import send_email
from flask import current_app, flash, request, render_template
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature


def auth_required(fn):
    @wraps(fn)
    def decorated(*args, **kwargs):
        endpoint = request.endpoint
        token = request.args.get('token', None)
        ser = URLSafeTimedSerializer(
            secret_key=current_app.config['SECRET_KEY'],
            salt=current_app.config['SALT'])

        if token is None:
            return authenticate(ser, endpoint)

        # Valid for 1 hour
        email, expired, invalid = deserialize_token(ser, token, 3600)
        if expired:
            flash('Link expired. Please request a new one.')
        elif invalid:
            flash('Invalid link. Please request a new one.')
        ok = not expired and not invalid

        if not ok:
            return authenticate(ser, endpoint)
        return fn(email, *args, **kwargs)
    return decorated


def generate_token(serializer, text):
    return serializer.dumps(text)


def deserialize_token(serializer, name, max_age=None):
    try:
        return serializer.loads(name, max_age=max_age), False, False
    except SignatureExpired:
        return None, True, False
    except BadSignature:
        return None, False, True
    return None, False, False


def authenticate(ser, route):
    form = EmailForm()
    if form.validate_on_submit():
        email = form.email.data
        customers = core.get_customers(email)
        if not customers:
            flash('No account found with that email.')
        else:
            token = generate_token(ser, email)
            send_email([email],
                    '{} email confirmation'.format(current_app.config['SHOP_NAME']),
                    'auth', token=token, route=route)
            flash('Email sent to {}'.format(email))
    return render_template('shop/auth.html', form=form)
