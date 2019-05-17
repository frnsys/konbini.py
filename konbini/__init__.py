import stripe
import easypost
from .routes import bp

class Konbini:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

        stripe.api_key = app.config['STRIPE_SECRET_KEY']
        easypost.api_key = app.config['EASYPOST_API_KEY']

        app.register_blueprint(bp, url_prefix='/shop')
