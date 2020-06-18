import stripe
import easypost
from konbini import core
from konbini.routes import bp

class Konbini:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

        stripe.api_key = app.config['STRIPE_SECRET_KEY']
        easypost.api_key = app.config['EASYPOST_API_KEY']

        url_prefix = app.config.get('KONBINI_URL_PREFIX', '/shop')
        app.register_blueprint(bp, url_prefix=url_prefix)

        self.app.get_products = core.get_products

        if app.config.get('KONBINI_INVOICE_SUB_SHIPPING') and 'KONBINI_SHIPPING_FROM' not in app.config:
            raise Exception('If you specify "KONBINI_INVOICE_SUB_SHIPPING", "KONBINI_SHIPPING_FROM" must also be set')
