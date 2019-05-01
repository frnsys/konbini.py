# konbini

A very simple storefront (no tracking, no user accounts, etc), basically a lightweight frontend for Stripe (goods/products and services/subscriptions) that integrates with EasyPost for shipping management and Mailgun for transactional emails.

# Setup

For development, you'll need `ngrok` or something similar to expose the local web application for webhooks.

## Stripe

Get your [Stripe API keys](https://dashboard.stripe.com/account/apikeys) and add them to `config.py`.

In the Stripe dashboard:
- Add products and SKUs (`Orders > Products`)
    - When adding products, make sure package dimensions and weights are set for each SKU to compute shipping costs.
- Add subscription products and plans (`Billing > Products`)
- Setup `checkout.session.completed` webhook (`Developers > Webhooks`), pointing to your `/checkout/completed` endpoint, e.g. `https://konbi.ni/checkout/completed`

## EasyPost

- easypost api key in relay, test key for test and so on

Get your [EasyPost API key](https://www.easypost.com/account/api-keys) and add it to `config.py`.

- In Stripe, go to [`Settings > Orders`](https://dashboard.stripe.com/account/relay/settings). For Live mode (and for development, Test mode), change shipping to `Provider > EasyPost` and paste in the API key (production key for Live mode, and test key for Test mode).