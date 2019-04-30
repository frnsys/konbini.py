# konbini

A very simple storefront, basically a lightweight frontend for Stripe (goods/products and services/subscriptions) that integrates with Shippo for shipping management and Mailgun for transactional emails.

Stripe's backend manages:
- products
- subscription plans
- tax settings
- shipping settings
- webhook configuration
    - in particular, setup a webhook for `checkout.session.completed`

For development, you'll need `ngrok` or something similar to expose the local web application for webhooks.

Setup Shippo-Stripe integration: <https://stripe.com/docs/orders/shippo>