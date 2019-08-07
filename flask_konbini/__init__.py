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
        self.app.get_plans = core.get_plans