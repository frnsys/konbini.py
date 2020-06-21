Current setup is basically as follows:

- There are two main "channels": _products_ (one-time payments) and _subscriptions_ (recurring payments). Note that in Stripe these are both called "products".
- Products
    - Stripe is used for inventory management, i.e. tracking SKUs and so on. We load products from here and people add them to their carts.
    - When someone starts a checkout process, we ask for:
        - Their email. Emails are used to identify customers. So we try to have one Stripe customer per email.
        - Their shipping address.
            - For US addresses, we validate.
        - This info, along with the cart, is passed to Stripe via `stripe.Order`. Based on the Stripe dashboard configuration, where y you set tax info (e.g. is tax calculated using a callback) and shipping info (e.g. is shipping calculated using a callback), stripe will automatically add tax and shipping to the order's line items.
            - Stripe's Order API is deprecated unfortunately, and they don't seem to have any plans to replace this functionality. So in the near future we may need to hit these tax (part of `konbini`, `/checkout/tax`)/shipping (EasyPost) callbacks ourselves (in addition to losing the inventory management aspect of the `Order` system). Note that we have `get_shipping_rate` which could be a drop-in replacement for the shipping cost calculation, though for multiple products we'd need to aggregate their dimensions to a complete package dimension...this seems hard (bin packing problem?).
                - <https://community.lightspeedhq.com/en/discussion/1214/how-does-shipping-api-handle-multiple-pieces-in-one-shipment>
                - <https://pypi.org/project/py3dbp/>
                - <https://pypi.org/project/pyShipping/>
                - **NOTE**: You must specify package dimensions as product metadata now, since Stripe does not officially support it anymore. This requires the following metadata values to be set: `'height', 'weight', 'length', 'width'` (inches and oz).
            - In any case, we then take the line items from this order and pass them to `stripe.Session` (which seems to be the recommended payment flow now) to use Stripe's Checkout feature. We use that to make the actual charge.
        - We have a webhook setup for successful checkouts, for the `checkout.session.completed` event. Note this fires for any successful checkout, whether for a product or a subscription, so we have to first determine which it is.
            - If it's a product checkout, we look for the associated order and then mark it as "paid" and also attach the associated payment intent ID (from the `stripe.Session`) so we can find it if need be.
            - Finally, we then we generate the shipping label (via EasyPost) and notify the specified parties (customer, fulfillment, etc, configured by `NEW_ORDER_RECIPIENTS`) of a new order.
- Subscriptions
    - Not all that different than the product system, except it _does not_ use `stripe.Order`. That is, we manually add shipping and tax line items. So worth looking at this if that all needs to be replaced.
    - Another difference is that subscriptions aren't added to a cart; when you select a subscription you're immediately taken to a checkout flow for that subscription only. Thus we are always only dealing with one subscription at a time and no subscription/product mixtures.
    - We ask for email (again to avoid duplicate customers), and shipping address if plan has metadata value `shipped = "true".`
    - After Stripe Checkout we again hook into the `checkout.session.completed` event. The handling here is not much different than for products, with a shipping label being generated if necessary.
    - Where subscriptions differ more is in the recurring payment part.
        - This requires notifying users of upcoming renewals, payment failures, etc. Stripe (recently?) provided ways to do this on your behalf, so `konbini` does not need to handle it as much.
            - The one thing that we do have to deal with is adding additional invoice items on top of the base subscription rate (i.e. shipping and tax). We hook into the `invoice.created` webhook event to do so.
        - This also requires letting customers update info, e.g. billing, shipping address, and cancelling. Stripe (also recently?) introduced a "self-serve portal" that lets people do this, so that was recently added.