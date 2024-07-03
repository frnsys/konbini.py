import stripe
import easypost
from konbini_dev import core
from konbini_dev.routes import bp

class Konbini:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

        app.csrf_protect.exempt('konbini.routes.checkout_completed_hook')

        stripe.api_key = app.config['STRIPE_SECRET_KEY']
        easypost.client = easypost.EasyPostClient(app.config['EASYPOST_API_KEY'])

        url_prefix = app.config.get('KONBINI_URL_PREFIX', '/shop')
        app.register_blueprint(bp, url_prefix=url_prefix)

        self.app.get_products = core.get_products

        if app.config.get('KONBINI_INVOICE_SUB_SHIPPING') and 'KONBINI_SHIPPING_FROM' not in app.config:
            raise Exception('If you specify "KONBINI_INVOICE_SUB_SHIPPING", "KONBINI_SHIPPING_FROM" must also be set')
