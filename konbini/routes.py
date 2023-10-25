import math
import stripe
from . import core, shipping
from .util import send_email
from .auth import auth_required
from .forms import EmailForm, ShippingForm
from pyusps import address_information
from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, redirect, request, session, abort, url_for, flash, current_app, jsonify

USPS_ADDRESS_KEYS = {
    'address': 'line1',
    'address_extended': 'line2',
    'state': 'state',
    'city': 'city',
    'zip5': 'postal_code'
}

bp = Blueprint('shop', __name__, template_folder='templates')


def is_in_stock(sku):
    return sku.metadata.get('sold_out') != 'true'

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

def normalize_address(address):
    """Normalize a domestic (US) address"""
    if address['country'] != 'US':
        return address, False

    addr = {
        'zip_code': address['postal_code'],
        'state': address['state'],
        'city': address['city'],
        'address': address['line1']
    }
    line2 = address.get('line2')
    if line2:
        addr['address_extended'] = line2
    try:
        usps_addr = address_information.verify(current_app.config['USPS_USER_ID'], addr)
        norm_addr = {}
        changed = False
        for k_frm, k_to in USPS_ADDRESS_KEYS.items():
            norm_addr[k_to] = usps_addr.get(k_frm)
            if (norm_addr[k_to] or '').lower() != (address[k_to] or '').lower():
                changed = True
        norm_addr['country'] = 'US'
        return norm_addr, changed
    except ValueError:
        return None, True

@bp.route('/')
def index():
    products = core.get_products()
    if request.args.get('format') == 'json':
        return jsonify(products=products)
    else:
        return render_template('shop/index.html', products=products)

@bp.route('/product/<id>')
def product(id):
    id = 'prod_{}'.format(id)
    try:
        product = stripe.Product.retrieve(id, expand=['default_price'])
    except stripe.error.InvalidRequestError as err:
        current_app.logger.debug(str(err))
        abort(404)
    if product is None or not product.active: abort(404)
    if product.type == 'good':
        skus = stripe.SKU.list(limit=100, product=id, active=True)['data']
        images = product.images + [s.image for s in skus if s.image and s.image not in product.images]
        for sku in skus:
            sku['in_stock'] = is_in_stock(sku)
        if request.args.get('format') == 'json':
            return jsonify(product=product, skus=skus, images=images)
        else:
            return render_template('shop/product.html', product=product, skus=skus, images=images)
    else:
        prices = stripe.Price.list(limit=100, product=id, active=True)['data']
        if request.args.get('format') == 'json':
            return jsonify(product=product, prices=prices, images=product.images)
        else:
            return render_template('shop/product.html', product=product, prices=prices, images=product.images)


@bp.route('/cart', methods=['GET', 'POST'])
def cart():
    if request.method == 'GET':
        subtotal = sum((int(session['meta'][id]['price']) * q for id, q in session.get('cart', {}).items() if q), 0)
        return render_template('shop/cart.html', subtotal=subtotal)

    name = request.form['name']
    sku_id = request.form['sku']
    product_id = request.form['product']
    quantity = request.form.get('quantity')
    if quantity and quantity is not None:
        quantity = int(quantity)

    if 'cart' not in session:
        session['cart'] = {}

    # If no quantity specified, add one
    if quantity is None:
        added = True
        session['cart'][sku_id] = session['cart'].get(sku_id, 0) + 1
    else:
        added = False
        session['cart'][sku_id] = quantity

    if 'meta' not in session:
        session['meta'] = {}

    # Delete item from cart if quantity is 0
    if quantity == 0 or quantity == '':
        del session['cart'][sku_id]

    # Otherwise, update product info
    else:
        if sku_id.startswith('sku_'):
            sku = stripe.SKU.retrieve(sku_id)
            price = sku.price
            interval = None
            interval_count = None
            exclude_tax = sku.metadata.get('exclude_tax') == 'true'
        elif sku_id.startswith('price_'):
            sku = stripe.Price.retrieve(sku_id)
            exclude_tax = sku.metadata.get('exclude_tax') == 'true'
            price = sku.unit_amount
            if sku.recurring:
                interval = sku.recurring.interval
                interval_count = sku.recurring.interval_count
            else:
                interval = None
                interval_count = None

        session['meta'][sku_id] = {
            'name': name,
            'price': price,
            'interval': interval,
            'interval_count': interval_count,
            'product_id': product_id,
            'exclude_tax': exclude_tax,
        }

    if added:
        flash('Added "{}" to cart.'.format(name), category='cart')
    else:
        flash('Cart updated.')

    if is_safe_url(request.referrer):
        return redirect(request.referrer)
    return redirect(url_for('shop.index'))

@bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('cart'):
        return redirect(url_for('shop.index'))

    form = ShippingForm()
    if not current_app.config.get('KONBINI_INTL_SHIPPING'):
        form.address.country.data = 'US'
        form.address.country.validators = []

    if form.validate_on_submit():
        session['email'] = form.data['email']
        address = {k: form.data['address'][k] for k in
                   ['line1', 'line2', 'city', 'state', 'postal_code', 'country']}
        address, changed = normalize_address(address)
        if address is None:
            return render_template('shop/shipping.html', form=form, invalid_address=True)

        session['shipping'] = {
            'name': form.data['name'],
            'address': address
        }

        return redirect(url_for('shop.pay', address_changed=True))
    return render_template('shop/shipping.html', form=form)

@bp.route('/checkout/pay')
def pay():
    if not session.get('shipping'):
        return redirect(url_for('shop.cart'))

    products = [(stripe.Product.retrieve(session['meta'][sku_id]['product_id'], expand=['default_price']), quantity)
            for sku_id, quantity in session['cart'].items()]
    rate, order_meta = shipping.get_shipping_rate(products, session['shipping'], **current_app.config)
    for k, v in session['shipping']['address'].items():
        order_meta['address_{}'.format(k)] = v
    order_meta['name'] = session['shipping']['name']

    items = [{
        'currency': 'usd',
        'name': session['meta'][sku_id]['name'],
        'amount': session['meta'][sku_id]['price'],
        'quantity': quantity,
        'exclude_tax': session['meta'][sku_id]['exclude_tax'],
    } for sku_id, quantity in session['cart'].items()]

    items.append({
        'currency': 'usd',
        'name': 'Shipping',
        'amount': rate,
        'quantity': 1,
        'exclude_tax': True
    })
    total = sum(i['amount'] for i in items)
    tax_total = sum(i['amount'] for i in items if not i['exclude_tax'])

    # Can't pass this to the session
    for i in items:
        del i['exclude_tax']

    tax_rates = stripe.TaxRate.list(limit=10)
    for tax in tax_rates:
        if tax['jurisdiction'] == session['shipping']['address']['state']:
            items.append({
                'name': 'Tax',
                'amount': math.ceil((tax.percentage/100) * tax_total),
                'currency': 'usd',
                'quantity': 1
            })

    kwargs = {
        'payment_method_types': ['card'],
        'line_items': items,
        'success_url': url_for('shop.checkout_success', _external=True),
        'cancel_url': url_for('shop.checkout_cancel', _external=True),
        'metadata': order_meta
    }

    # Try to find customer with existing email
    customers = core.get_customers(session['email'])
    if customers:
        kwargs['customer'] = customers[0].id
    else:
        kwargs['customer_email'] = session['email']

    address_changed = request.args.get('address_changed')
    session['stripe'] = stripe.checkout.Session.create(**kwargs)

    total = sum(i['amount'] for i in items)
    return render_template('shop/pay.html',
            total=total,
            items=items,
            shipping=session['shipping'],
            address_changed=address_changed)

@bp.route('/checkout/success')
def checkout_success():
    for k in ['cart', 'plan', 'stripe', 'shipping']:
        if k in session: del session[k]
    return render_template('shop/thanks.html')

@bp.route('/checkout/cancel')
def checkout_cancel():
    return 'cancelled' # TODO

@bp.route('/subscribe/bill', methods=['POST'])
def subscribe_invoice_hook():
    payload = request.data
    sig_header = request.headers['Stripe-Signature']
    event = stripe.Webhook.construct_event(
        payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRETS']['invoice.created']
    )

    if event['type'] == 'invoice.created':
        invoice = event['data']['object']

        # This event still gets called even if the invoice
        # is no longer in draft form, ignore to avoid errors
        # We have to manually retrieve the latest invoice object,
        # because the one sent to the endpoint may not be up-to-date
        invoice = stripe.Invoice.retrieve(invoice['id'])
        if invoice['status'] != 'draft': return '', 200

        cus = stripe.Customer.retrieve(invoice['customer'])
        has_payment_method = cus['default_source'] is not None

        # Only do the following if we can even charge
        if has_payment_method:
            sub = stripe.Subscription.retrieve(invoice['subscription'])
            prod = stripe.Product.retrieve(sub['plan']['product'], expand=['default_price'])
            if prod['metadata'].get('shipped') == 'true':
                # Check that there is a valid address for the customer
                shipping_info = cus['shipping'] or {}
                sub_metadata = sub.get('metadata', {})
                addr = shipping_info.get('address', sub_metadata)
                name = shipping_info.get('name', sub_metadata.get('name', None))
                has_customer_address = name is not None and addr and all(v != 'nan' for v in addr.values())
                if has_customer_address:
                    shipping_info = {
                        'name': name,
                        'address': addr
                    }

                    # Check for applicable tax rates
                    if not prod['metadata'].get('exclude_tax') == 'true':
                        tax_rates = stripe.TaxRate.list(limit=10)
                        app_tax = None
                        for tax in tax_rates:
                            if tax['jurisdiction'] == shipping_info['address']['state']:
                                app_tax = tax
                                break
                        if app_tax is not None:
                            stripe.Invoice.modify(invoice['id'], default_tax_rates=[app_tax.id])

                    if current_app.config.get('KONBINI_INVOICE_SUB_SHIPPING'):
                        # Calculate shipping estimate
                        prod_id = prod['metadata']['shipped_product_id']
                        product = stripe.Product.retrieve(prod_id)
                        rate, _ = shipping.get_shipping_rate([(product, 1)], shipping_info, **current_app.config)

                        # Add the item to this invoice
                        stripe.InvoiceItem.create(
                            customer=cus['id'],
                            invoice=invoice['id'],
                            amount=rate,
                            currency='usd',
                            description='Shipping',
                        )

    return '', 200


@bp.route('/checkout/completed', methods=['POST'])
def checkout_completed_hook():
    new_order_recipients = current_app.config['NEW_ORDER_RECIPIENTS']
    payload = request.data
    sig_header = request.headers['Stripe-Signature']
    event = stripe.Webhook.construct_event(
        payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRETS']['checkout.session.completed']
    )

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # If subscription is set,
        # assume that this is a checkout
        # for a subscription only
        if session['subscription'] is not None:
            sub_id = session['subscription']
            cus_id = session['customer']
            line_items = [li for li in session['display_items'] if li['type'] == 'custom']
            sub = stripe.Subscription.retrieve(sub_id)
            meta = sub.metadata
            if meta:
                name = meta.pop('name')
                addr = meta
                shipping_info = {'name': name, 'address': addr}
                stripe.Customer.modify(cus_id, name=name, shipping=shipping_info)
            else:
                name = ''
                shipping_info = {}

            meta = session['metadata']
            shipment_meta = {}
            if meta['shipment_id'] is not None:
                # shipment_id = meta['shipment_id']
                exists, tracking_url = shipping.shipment_exists, (meta['shipment_id'])
                if not exists:
                    shipment_meta = shipping.buy_shipment(name=name, **meta) # shipment_id already in meta
                else:
                    shipment_meta = {'tracking_url': tracking_url}

            send_email(new_order_recipients,
                       'New subscription', 'new_subscription',
                       subscription=sub, line_items=line_items, shipping=shipping_info, label_url=shipment_meta.get('label_url'))

            # Notify customer
            customer = stripe.Customer.retrieve(cus_id)
            customer_email = customer['email']
            send_email([customer_email], 'Thank you for your subscription', 'complete_subscription',
                       subscription=sub, line_items=line_items, tracking_url=shipment_meta.get('tracking_url'))
            return '', 200

        else:
            # Get associated payment,
            # check its state
            pi = stripe.PaymentIntent.retrieve(session['payment_intent'])
            if pi['status'] != 'succeeded' or pi['charges']['data'][0]['refunded']:
                return '', 200

            completed = pi['metadata'].get('completed')
            if completed:
                return '', 200

            customer_id = session['customer']
            customer = stripe.Customer.retrieve(customer_id)
            customer_email = customer['email']

            # Purchase shipping label
            meta = session['metadata']
            # shipment_id = meta['shipment_id']
            exists, tracking_url = shipping.shipment_exists(meta['shipment_id'])
            if not exists:
                shipment_meta = shipping.buy_shipment(**meta) # shipment_id already in meta
            else:
                shipment_meta = {'tracking_url': tracking_url}

            # Mark as completed
            stripe.PaymentIntent.modify(session['payment_intent'], metadata={'completed': True})

            line_items = stripe.checkout.Session.list_line_items(session['id'], limit=100)['data']
            items = [{
                'amount': i['amount_total'],
                'quantity': i['quantity'],
                'description': i['description']
            } for i in line_items]

            # Notify fulfillment person
            send_email(new_order_recipients,
                       'New order placed', 'new_order',
                       order=pi, items=items, label_url=shipment_meta.get('label_url'))

            # Notify customer
            send_email([customer_email], 'Thank you for your order', 'complete_order',
                    order=pi, items=items, tracking_url=shipment_meta.get('tracking_url'))
    return '', 200


@bp.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        name = request.form['name']
        price_id = request.form['sku']

        try:
            price = stripe.Price.retrieve(price_id)
        except stripe.error.InvalidRequestError:
            return redirect(url_for('shop.index'))
        product = stripe.Product.retrieve(price.product)

        shipped = product.metadata.get('shipped') == 'true'
        session['plan'] = {
            'name': name,
            'amount': price.unit_amount,
            'prod_id': product.id,
            'price_id': price_id,
            'shipped': shipped
        }

    if not session.get('plan'):
        return redirect(url_for('shop.index'))

    if session['plan']:
        # If the session requires shipping info,
        # ensure that the address has been set
        if session['plan'].get('shipped') \
            and not session['plan'].get('address'):
            return redirect(url_for('shop.subscribe_address'))

        # Otherwise, just ensure that we have an email
        elif not session.get('email'):
            return redirect(url_for('shop.subscribe_email'))

    line_items = []
    shipment_id = None
    if session['plan'].get('shipped'):
        addr = session['plan']['address']
        addr = {
            'name': addr['name'],
            'address': addr
        }

        if current_app.config.get('KONBINI_INVOICE_SUB_SHIPPING'):
            prod_id = session['plan']['prod_id']
            plan_prod = stripe.Product.retrieve(prod_id)
            prod_id = plan_prod['metadata']['shipped_product_id']
            product = stripe.Product.retrieve(prod_id)
            rate, order_meta = shipping.get_shipping_rate([(product, 1)], addr, **current_app.config)
            shipment_id = order_meta['shipment_id']
            line_items.append({
                'name': 'Shipping',
                'description': 'Shipping',
                'amount': rate,
                'currency': 'usd',
                'quantity': 1
            })

        tax_rates = stripe.TaxRate.list(limit=10)
        for tax in tax_rates:
            if tax['jurisdiction'] == addr['address']['state']:
                line_items.append({
                    'name': 'Tax',
                    'description': 'Tax',
                    'amount': math.ceil((tax.percentage/100) * session['plan']['amount']),
                    'currency': 'usd',
                    'quantity': 1
                })

    kwargs = {
        'payment_method_types': ['card'],
        'line_items': line_items,
        'subscription_data' :{
            'items': [{
                'plan':  session['plan']['price_id']
            }],
            'metadata': session['plan'].get('address')
        },
        'metadata': {
            'shipment_id': shipment_id,
            'address': session['plan'].get('address')
        },
        'allow_promotion_codes': True,
        'success_url': url_for('shop.checkout_success', _external=True),
        'cancel_url': url_for('shop.checkout_cancel', _external=True)
    }

    # Try to find customer with existing email
    customers = core.get_customers(session['email'])
    if customers:
        kwargs['customer'] = customers[0].id
    else:
        kwargs['customer_email'] = session['email']

    session['stripe'] = stripe.checkout.Session.create(**kwargs)

    total = sum(i['amount'] for i in line_items) + session['plan']['amount']
    address_changed = request.args.get('address_changed')
    return render_template('shop/subscribe.html',
            total=total,
            address_changed=address_changed,
            line_items=line_items, **session['plan'])


@bp.route('/subscribe/address', methods=['GET', 'POST'])
def subscribe_address():
    if not session.get('plan'):
        return redirect(url_for('shop.index'))

    form = ShippingForm()

    if not current_app.config.get('KONBINI_INTL_SHIPPING'):
        form.address.country.data = 'US'
        form.address.country.validators = []

    if form.validate_on_submit():
        session['email'] = form.data['email']
        address = {k: form.data['address'][k] for k in
                   ['line1', 'line2', 'city', 'state', 'postal_code', 'country']}
        address, changed = normalize_address(address)
        if address is None:
            return render_template('shop/shipping.html', form=form, invalid_address=True)
        address['name'] = form.data['name']

        # So the session update property persists
        plan = session['plan']
        plan['address'] = address
        session['plan'] = plan

        return redirect(url_for('shop.subscribe', address_changed=True))
    return render_template('shop/shipping.html', form=form)


@bp.route('/subscribe/email', methods=['GET', 'POST'])
def subscribe_email():
    if not session.get('plan'):
        return redirect(url_for('shop.index'))

    form = EmailForm()
    if form.validate_on_submit():
        session['email'] = form.data['email']
        return redirect(url_for('shop.subscribe', address_changed=False))
    return render_template('shop/email.html', form=form)


@bp.route('/checkout/tax', methods=['POST'])
def tax():
    data = request.get_json()
    order = data['order']

    addr = order['shipping']['address']
    tax = None
    for t in current_app.config['TAXES']:
        if all(addr[k] == v for k, v in t['address'].items()):
            tax = t
            break

    if tax is not None:
        order_update = {
            'items': [{
                'parent': None,
                'type': 'tax',
                'description': 'Sales tax',
                'amount': math.ceil(order['amount'] * tax['amount']),
                'currency': 'usd'
            }]
        }
    else:
        order_update = {'items': []}

    return jsonify(order_update=order_update)


@bp.route('/subscribe/manage', methods=['GET', 'POST'])
def manage_subscription():
    """Send link to Stripe's self-serve portal"""
    form = EmailForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form.data['email']
            customers = core.get_customers(email)

            urls = []
            for cus in customers:
                if cus.subscriptions:
                    res = stripe.billing_portal.Session.create(
                        customer=cus.id,
                        return_url=url_for('shop.manage_subscription', _external=True),
                    )
                    urls.append(res['url'])

            if urls:
                send_email([email],
                       'Manage your subscriptions', 'manage_subscriptions',
                       urls=urls)

            flash('We will send a link to manage subscriptions matching that email address if any are found.')
            return render_template('shop/manage.html', form=form)
    return render_template('shop/manage.html', form=form)


@bp.route('/subscribe/billing', methods=['GET', 'POST'])
@auth_required
def update_billing(email=None):
    if request.method == 'POST':
        card_token = request.form.get('stripeToken')
        if card_token is not None:

            # Get customers with email
            customers = core.get_customers(email)

            # Update across all customers with matching email
            for cus in customers:
                if cus.subscriptions:
                    stripe.Customer.modify(cus.id, source=card_token)

            flash('Billing information successfully updated.')

    return render_template('shop/billing.html', email=email)
