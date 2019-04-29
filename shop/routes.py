import config
import stripe
stripe.api_key = config.STRIPE_SECRET_KEY

from flask import Blueprint

bp = Blueprint('main', __name__)

@bp.route('checkout')
def checkout():
    pass