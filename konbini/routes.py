import math
import stripe
import easypost
from . import core
from flask_mail import Message
from .forms import ShippingForm
from pyusps import address_information
from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, redirect, request, session, abort, url_for, flash, current_app, jsonify

# Only supporting domestic (US) shipping;
# incorporating international shipping is
# too complicated at this point
SHIPPING_COUNTRY = 'US'
USPS_ADDRESS_KEYS = {
    'address': 'line1',
    'address_extended': 'line2',
    'state': 'state',
    'city': 'city',
    'zip5': 'postal_code'
}

bp = Blueprint('shop', __name__, template_folder='templates')

def send_email(to, subject, template, reply_to=None, bcc=None, **kwargs):
    reply_to = reply_to or current_app.config['MAIL_REPLY_TO']
    msg = Message(subject,
                body=render_template('shop/email/{}.txt'.format(template), **kwargs),
                html=render_template('shop/email/{}.html'.format(template), **kwargs),
                recipients=[to],
                reply_to=reply_to,
                bcc=bcc)
    mail = current_app.extensions.get('mail')
    mail.send(msg)

def is_in_stock(sku):
    inv = sku['inventory']
    if inv['type'] == 'bucket' and inv['value'] == 'out_of_stock':
        return False
    elif inv['type'] == 'finite' and inv['quantity'] == 0:
        return False
    return True

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

def normalize_address(address):
    """Normalize a domestic (US) address"""
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
        return norm_addr, changed
    except ValueError:
        return None, True

@bp.route('/')
def index():
    products = core.get_products()
    plans = core.get_plans()
    if request.args.get('format') == 'json':
        return jsonify(products=products, plans=plans)
    else:
        return render_template('shop/index.html', products=products, plans=plans)

@bp.route('/products')
def products():
    products = core.get_products()
    if request.args.get('format') == 'json':
        return jsonify(results=products)
    else:
        return render_template('shop/products.html', products=products)

@bp.route('/product/<id>')
def product(id):
    id = 'prod_{}'.format(id)
    product = stripe.Product.retrieve(id)
    if product is None or not product.active: abort(404)
    skus = stripe.SKU.list(limit=100, product=id, active=True)['data']
    images = product.images + [s.image for s in skus if s.image and s.image not in product.images]
    for sku in skus:
        sku['in_stock'] = is_in_stock(sku)
    if request.args.get('format') == 'json':
        return jsonify(product=product, skus=skus, images=images)
    else:
        return render_template('shop/product.html', product=product, skus=skus, images=images)

@bp.route('/plans')
def plans():
    plans = core.get_plans()
    if request.args.get('format') == 'json':
        return jsonify(results=plans)
    else:
        return render_template('shop/plans.html', plans=plans)

@bp.route('/plans/<id>')
def plan(id):
    id = 'prod_{}'.format(id)
    product = stripe.Product.retrieve(id)
    if product is None or not product.active: abort(404)
    plans = stripe.Plan.list(limit=100, product=id, active=True)['data']
    if request.args.get('format') == 'json':
        return jsonify(product=product, plans=plans)
    else:
        return render_template('shop/plan.html', product=product, plans=plans)

@bp.route('/cart', methods=['GET', 'POST'])
def cart():
    if request.method == 'GET':
        subtotal = sum((session['meta'][id]['price'] * q for id, q in session.get('cart', {}).items()), 0)
        return render_template('shop/cart.html', subtotal=subtotal)

    name = request.form['name']
    sku_id = request.form['sku']
    quantity = request.form.get('quantity')
    if quantity is not None:
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
    if quantity == 0:
        del session['cart'][sku_id]

    # Otherwise, update product info
    else:
        if sku_id.startswith('sku_'):
            sku = stripe.SKU.retrieve(sku_id)
            price = sku.price
            interval = None
        elif sku_id.startswith('plan_'):
            sku = stripe.Plan.retrieve(sku_id)
            price = sku.amount
            interval = sku.interval
        session['meta'][sku_id] = {
            'name': name,
            'price': price,
            'interval': interval
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
    if form.validate_on_submit():
        address = {k: form.data['address'][k] for k in
                   ['line1', 'line2', 'city', 'state', 'postal_code']}
                   # ['line1', 'line2', 'city', 'state', 'country', 'postal_code']}
        address, changed = normalize_address(address)
        if address is None:
            return render_template('shop/shipping.html', form=form, invalid_address=True)
        address['country'] = SHIPPING_COUNTRY
        order = stripe.Order.create(
            currency='usd',
            items=[{
                'type': 'sku',
                'parent': sku_id,
                'quantity': quantity,
                'amount': session['meta'][sku_id]['price'],
                'description': session['meta'][sku_id]['name']
            } for sku_id, quantity in session['cart'].items()],
            shipping={
                'name': form.data['name'],
                'address': address
            })

        # Choose the cheapest shipping option
        if order['shipping_methods']:
            cheapest_shipping = min(order['shipping_methods'], key=lambda sm: sm['amount'])
            session['order'] = stripe.Order.modify(
                order['id'],
                selected_shipping_method=cheapest_shipping['id']
            )
        return redirect(url_for('shop.pay', address_changed=True))
    return render_template('shop/shipping.html', form=form)

@bp.route('/checkout/pay')
def pay():
    if not session.get('order'):
        return redirect(url_for('shop.cart'))

    address_changed = request.args.get('address_changed')
    session['stripe'] = stripe.checkout.Session.create(
        client_reference_id=session['order']['id'],
        payment_method_types=['card'],
        line_items=[{
            'name': item['description'],
            'amount': item['amount'],
            'currency': item['currency'],
            'quantity': item['quantity'] or 1,
        } for item in session['order']['items']],
        success_url=url_for('shop.checkout_success', _external=True),
        cancel_url=url_for('shop.checkout_cancel', _external=True))

    return render_template('shop/pay.html', address_changed=address_changed)

@bp.route('/checkout/success')
def checkout_success():
    for k in ['cart', 'plan', 'stripe', 'order']:
        if k in session: del session[k]
    return render_template('shop/thanks.html')

@bp.route('/checkout/cancel')
def checkout_cancel():
    return 'cancelled' # TODO

@bp.route('/checkout/completed', methods=['POST'])
def checkout_completed_hook():
    payload = request.data
    sig_header = request.headers['Stripe-Signature']
    event = stripe.Webhook.construct_event(
        payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
    )

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # If subscription is set,
        # assume that this is a checkout
        # for a subscription only
        if session['subscription'] is not None:
            return '', 200

        else:
            # Get associated order,
            # check its state
            order_id = session['client_reference_id']
            order = stripe.Order.retrieve(order_id)
            if order['status'] != 'created':
                return '', 200

            # Associate payment id with this order
            stripe.Order.modify(order_id, metadata={'payment': session['payment_intent']})

            # print(session)
            # print(order)

            customer_id = session['customer']
            customer = stripe.Customer.retrieve(customer_id)
            customer_email = customer['email']

            # Create shipping label
            shipment = easypost.Shipment.retrieve(order.id)
            rate = next(r for r in shipment.rates if r['id'] == order.selected_shipping_method)
            shipment.buy(rate=rate)
            # print(shipment)

            items = [{
                'amount': i['amount'],
                'quantity': i['quantity'],
                'description': i['description']
            } for i in  order['items']]

            # Notify fulfillment person
            label_url = shipment.postage_label.label_url
            send_email(current_app.config['NEW_ORDER_RECIPIENT'],
                       'New order placed', 'new_order',
                       order=order, items=items, label_url=label_url)

            # Notify customer
            tracking_url = shipment.tracker.public_url
            send_email(customer_email, 'Thank you for your order', 'complete_order', order=order, items=items, tracking_url=tracking_url)

    return '', 200

@bp.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        plan_id = request.form['id']

        try:
            plan = stripe.Plan.retrieve(plan_id)
        except stripe.error.InvalidRequestError:
            return redirect(url_for('shop.plans'))
        product = stripe.Product.retrieve(plan.product)

        shipped = product.metadata.get('shipped') == 'true'
        session['plan'] = {
            'name': name,
            'price': price,
            'plan_id': plan_id,
            'shipped': shipped
        }

    if not session['plan']:
        return redirect(url_for('shop.plans'))

    # If the session requires shipping info,
    # ensure that the address has been set
    if session['plan'] and session['plan'].get('shipped') \
            and not session['plan'].get('address'):
        return redirect(url_for('shop.subscribe_address'))

    session['stripe'] = stripe.checkout.Session.create(
        payment_method_types=['card'],
        subscription_data={
            'items': [{
                'plan':  session['plan']['plan_id']
            }],
            'metadata': session['plan'].get('address')
        },
        success_url=url_for('shop.checkout_success', _external=True),
        cancel_url=url_for('shop.checkout_cancel', _external=True))

    address_changed = request.args.get('address_changed')
    return render_template('shop/subscribe.html', address_changed=address_changed, **session['plan'])

@bp.route('/subscribe/address', methods=['GET', 'POST'])
def subscribe_address():
    if not session['plan']:
        return redirect(url_for('shop.plans'))

    form = ShippingForm()
    if form.validate_on_submit():
        address = {k: form.data['address'][k] for k in
                   ['line1', 'line2', 'city', 'state', 'postal_code']}
                   # ['line1', 'line2', 'city', 'state', 'country', 'postal_code']}
        address, changed = normalize_address(address)
        if address is None:
            return render_template('shop/shipping.html', form=form, invalid_address=True)
        address['country'] = SHIPPING_COUNTRY
        address['name'] = form.data['name']

        # So the session update property persists
        plan = session['plan']
        plan['address'] = address
        session['plan'] = plan

        return redirect(url_for('shop.subscribe', address_changed=True))
    return render_template('shop/shipping.html', form=form)


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