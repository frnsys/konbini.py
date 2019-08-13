# konbini

A very simple storefront (no tracking, no user accounts, etc), basically a lightweight frontend for Stripe (goods/products and services/subscriptions) that integrates with EasyPost for shipping management and Mailgun for transactional emails.

Currently `konbini` only supports domestic (US) shipping.

# Setup

__This setup is necessary for using Konbini as either a standalone app or as a Flask extension.__

For development, you'll need `ngrok` or something similar to expose the local web application for webhooks.

## Stripe

Get your [Stripe API keys](https://dashboard.stripe.com/account/apikeys) and add them to `config.py`, e.g.:

```
STRIPE_PUBLIC_KEY = 'pk_...'
STRIPE_SECRET_KEY = 'sk_...'
```

In the Stripe dashboard:
- Add products and SKUs (`Orders > Products`)
    - When adding products, make sure package dimensions and weights are set for each SKU to compute shipping costs.
- Add subscription products and plans (`Billing > Products`)
- Setup `checkout.session.completed` webhook (`Developers > Webhooks`), pointing to your `/checkout/completed` endpoint, e.g. `https://konbi.ni/checkout/completed`. You'll get a webhook secret, add it to `config.py`, e.g.:

```
STRIPE_WEBHOOK_SECRET = 'whsec_...'
```

## EasyPost

Get your [EasyPost API key](https://www.easypost.com/account/api-keys) and add it to `config.py`, e.g.:

```
EASYPOST_API_KEY = 'EZ...'
```

- In Stripe, go to [`Settings > Orders`](https://dashboard.stripe.com/account/relay/settings). For Live mode (and for development, Test mode), change shipping to `Provider > EasyPost` and paste in the API key (production key for Live mode, and test key for Test mode).

## Taxes

In `config.py` you should also specify tax conditions, e.g.:

```
TAXES = [{
    'address': {
        'state': 'NY',
        'country': 'US'
    },
    'amount': 0.08875
}]
```

When a checkout occurs, the tax amount will be computed using the first matching tax.

Stripe does provide integrations with paid tax calculation services which are probably better if your situation is more complex.

## USPS Address verification (US only)

`konbini` uses USPS's address verification service to normalize (US) addresses.

- Register to use USPS's web tools here: <https://registration.shippingapis.com/>
- USPS will email you a user ID, add that to `config.py` as `USPS_USER_ID`

## Additional configuration

In `config.py`:

```
# What email gets notified when new orders are placed
NEW_ORDER_RECEIPIENT = 'foo@foo.com'

# Config for Flask-Mail
MAIL_SERVER = '...'
MAIL_USERNAME = '...'
MAIL_PASSWORD = '...'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_DEFAULT_SENDER = '...'
MAIL_REPLY_TO = '...'
```

# As a Standalone App

Setup as you would any other Flask app. To try it out, you can run `app.py`.

## Themes

You can override the templates for `konbini` by creating templates in your app's `templates/shop` folder.

# As a Flask Extension

This isn't yet published to pypi, so install with:

    pip install git+https://github.com/frnsys/konbini

To use as a Flask extension:

```
from flask_mail import Mail
from flask_konbini import Konbini

# Setup your app...

# Konbini requires the Flask-Mail extension
Mail(app)

Konbini(app)
```

This sets Konbini up at `/shop`.

## Themes

When using as an extension, templates can be overridden by adding new templates to `templates/shop` in your Flask application. Their filenames should match what you see in `konbini/templates/shop` in this repo.