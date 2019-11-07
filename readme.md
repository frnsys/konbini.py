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
    - **Make sure you include at least one SKU for a product.**
    - When adding products, __make sure package dimensions and weights are set for each SKU to compute shipping costs__. Otherwise they will be ignored.
- Add subscription products and plans (`Billing > Products`)
    - Note that if a subscription product requires shipping information, add a metadata field called `shipped` and set its value to `true`. **Also note that this does _not_ automatically generate shipping labels; this assumes you have your own process for shipping out subscription items.**
        - You can, however set `KONBINI_INVOICE_SUB_SHIPPING = True` to add shipping costs when a subscription payment is invoiced. This still does not create the label, though. **If you use this, you must set `KONBINI_SHIPPING_FROM` (see below) and your subscription product metadata must also have a field called `shipped_product_id` set to the product id to be shipped. This product must have package dimensions and weight defined.**
- Add tax rates (used for subscriptions) (`Billing > Tax Rates`). These match the customer shipping address `state` field to the tax rate's `Region` value. E.g. if you want to set an NY sales tax, set tax rate `Region` to `NY`, and whenever a subscription shipping address has `NY` for the `state` field, the tax will be applied to each invoice.
- Setup webhooks (`Developers > Webhooks`)
    - For automatically generating shipping labels and sending order confirmation emails, setup a `checkout.session.completed` webhook, pointing to your `/checkout/completed` endpoint, e.g. `https://konbi.ni/shop/checkout/completed`.
    - For automatically adding taxes to subscriptions, setup a `invoice.created` webhook, pointing to your `/subscribe/bill` endpoint, e.g. `https://konbi.ni/shop/subscribe/bill`.
    - For each of these you'll get a webhook secret, add them to `config.py` like so:

```
STRIPE_WEBHOOK_SECRETS = {
    'checkout.session.completed': 'whsec_...',
    'invoice.created': 'whsec_...'
}
```

## EasyPost

Get your [EasyPost API key](https://www.easypost.com/account/api-keys) and add it to `config.py`, e.g.:

```
EASYPOST_API_KEY = 'EZ...'
```

- In Stripe, go to [`Settings > Orders`](https://dashboard.stripe.com/account/relay/settings). For Live mode (and for development, Test mode), change `Shipping` to `Provider > EasyPost` and paste in the API key (production key for Live mode, and test key for Test mode).

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

When a product (non-subscription) checkout occurs, the tax amount will be computed using the first matching tax. For subscriptions, see the Stripe setup above.

In Stripe, go to [`Settings > Orders`](https://dashboard.stripe.com/account/relay/settings). For Live mode (and for development, Test mode), change `Taxes` to `Callback` and in the `Callback` field add `https://yoursite/shop/checkout/tax` (change `shop` as needed to your `KONBINI_URL_PREFIX`).

Stripe does provide integrations with paid tax calculation services which are probably better if your situation is more complex.

## USPS Address verification (US only)

`konbini` uses USPS's address verification service to normalize (US) addresses.

- Register to use USPS's web tools here: <https://registration.shippingapis.com/>
- USPS will email you a user ID, add that to `config.py` as `USPS_USER_ID`

## Additional configuration

In `config.py`:

```
# Your shop name
SHOP_NAME = 'Foo'

# What email gets notified when new orders are placed
NEW_ORDER_RECIPIENT = 'foo@foo.com'

# The email sender
MAIL_REPLY_TO = 'foo@foo.com'

# Config for Flask-Mail
MAIL_SERVER = '...'
MAIL_USERNAME = '...'
MAIL_PASSWORD = '...'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_DEFAULT_SENDER = '...'
MAIL_REPLY_TO = '...'

# Shipping from address
# Note this looks redundant to the shipping setting in Stripe;
# Stripe does not provide API access to that setting so it's repeated here
# for subscription shipping (see above).
KONBINI_SHIPPING_FROM = {
    'name': '...',
    'street1': '...',
    'street2': '...',
    'city': '...',
    'state': '...',
    'zip': '...',
    'country': '...'
}
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

## Customer management

`konbini` is very simple and doesn't provide any customer management tools. If you need to update shipping addresses, issue refunds, etc, please do so through the Stripe dashboard.