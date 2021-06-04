# konbini

A very simple storefront (no tracking, no user accounts, etc), basically a lightweight frontend for Stripe (goods/products and services/subscriptions) that integrates with EasyPost or ShipBob for shipping management and Mailgun for transactional emails.

`konbini` supports both domestic (US) and international shipping (disabled by default, see below), but has very limited support for customs.

Currently `konbini` assumes you are operating in the US...I would like to change that, but it's already complicated enough dealing with e-commerce and shipping in one country. Help is of course always welcome.

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
- Add products (`Products`)
    - When adding products, __make sure package dimensions and weights are set for each SKU to compute shipping costs__. Otherwise they will be ignored.
        - The dimensions and weights must be set as metadata on the product. Stripe used to support them as first-class fields, but not anymore. Use the keys `height` (in), `width` (in), `length` (in), and `weight` (oz).
- Add subscription products and plans (`Billing > Products`)
    - Note that if a subscription product requires shipping information, add a metadata field called `shipped` and set its value to `true`. This will automatically generate a shipping label _only for when the person initially subscribes_. Any subsequent labels (e.g. if a new issue is published and needs to be sent out to active subscribers) will have to be generated manually.
        - You can, however set `KONBINI_INVOICE_SUB_SHIPPING = True` to add shipping costs when a subscription payment is invoiced. This still does not create the label, though. **If you use this, you must set `KONBINI_SHIPPING_FROM` (see below) and your subscription product metadata must also have a field called `shipped_product_id` set to the product id to be shipped. This product must have package dimensions and weight defined.** Also see the note below on international shipping.
- Add tax rates (used for subscriptions) (`Billing > Tax Rates`). These match the customer shipping address `state` field to the tax rate's `Region` value. E.g. if you want to set an NY sales tax, set tax rate `Region` to `NY`, and whenever a subscription shipping address has `NY` for the `state` field, the tax will be applied to each invoice.
    - If a product should be excluded from tax calculations, add a metadata field called `exclude_tax` and set its value to `true`.
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

### Shipping

## EasyPost

Add this to your config:

```
KONBINI_SHIPPER = 'easypost'
```

Then get your [EasyPost API key](https://www.easypost.com/account/api-keys) and add it to `config.py`, e.g.:

```
EASYPOST_API_KEY = 'EZ...'
```

## ShipBob

Add this to your config:

```
KONBINI_SHIPPER = 'shipbob'
```

Then get your [ShipBob API key](https://developer.shipbob.com/) and add it to `config.py`, e.g.:

```
SHIPBOB_API_KEY = '...'
SHIPBOB_CHANNEL_ID = '...'
```

Add your products to ShipBob and then in Stripe for each of your products you must add a new metadata field called `shipbob_inventory_id` and set it to the corresponding ShipBob inventory ID for that product.

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

Stripe does provide integrations with paid tax calculation services which are probably better if your situation is more complex.

## USPS Address verification (US only)

`konbini` uses USPS's address verification service to normalize (US) addresses.

- Register to use USPS's web tools here: <https://registration.shippingapis.com/>
- USPS will email you a user ID, add that to `config.py` as `USPS_USER_ID`

## Additional configuration

In `config.py`:

```
# For user email authentication
SECRET_KEY = '...'
EMAIL_SALT = '...'

# Your shop name
SHOP_NAME = 'Foo'

# What emails gets notified when new orders are placed
NEW_ORDER_RECIPIENTS = ['foo@foo.com']

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
    'country': '...',
    'phone': '4153334444
}
```

# International shipping

I believe ShipBob handles international shipping and customs for you.

If you're using EasyPost, `konbini` provides very, very basic support for international shipping. To use it, add this to your config:

```
KONBINI_INTL_SHIPPING = True
```

All this really does is allow non-US addresses to be used for shipping. As noted above, only US addresses will be validated.

If you are planning on doing international shipping, you will also want to supply some [basic customs information](https://www.easypost.com/customs-guide#step2):

```
KONBINI_CUSTOMS = {
    'contents_type': 'merchandise',
    'contents_explanation': None,
    'restriction_type': 'none',
    'restriction_comments': None,
    'customs_certify': True,
    'customs_signer': 'Your Name',
    'non_delivery_option': 'return',
    'eel_pfc': 'NOEEI 30.37(a)'
}
```

Currently this is only used to estimate shipping rates, and only for products shipped as a part of subscriptions. This is _not_ added to shipping labels. See the note for `KONBINI_INVOICE_SUB_SHIPPING` above.

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