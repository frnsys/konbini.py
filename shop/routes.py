import stripe
from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, redirect, request, session, abort, url_for, flash

bp = Blueprint('main', __name__)

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


@bp.route('/')
def products():
    products = stripe.Product.list(limit=100, active=True, type='good')['data']
    return render_template('products.html', products=products)

@bp.route('/product/<id>')
def product(id):
    id = 'prod_{}'.format(id)
    product = stripe.Product.retrieve(id)
    if product is None or not product.active: abort(404)
    skus = stripe.SKU.list(limit=100, product=id, active=True)['data']
    images = set(product.images + [s.image for s in skus])
    return render_template('product.html', product=product, skus=skus, images=images)

@bp.route('/plans')
def plans():
    plans = stripe.Product.list(limit=100, active=True, type='service')['data']
    return render_template('plans.html', plans=plans)

@bp.route('/plans/<id>')
def plan(id):
    id = 'prod_{}'.format(id)
    product = stripe.Product.retrieve(id)
    if product is None or not product.active: abort(404)
    plans = stripe.Plan.list(limit=100, product=id, active=True)['data']
    return render_template('plan.html', product=product, plans=plans)

@bp.route('/cart', methods=['GET', 'POST'])
def cart():
    if request.method == 'GET':
        subtotal = sum(session['meta'][id]['price'] * q for id, q in session['cart'].items())
        return render_template('cart.html', subtotal=subtotal)

    name = request.form['name']
    sku_id = request.form['sku']

    sku = stripe.SKU.retrieve(sku_id)
    price = sku.price

    if 'cart' not in session:
        session['cart'] = {}
    session['cart'][sku_id] = session['cart'].get(sku_id, 0) + 1

    if 'meta' not in session:
        session['meta'] = {}
    session['meta'][sku_id] = {
        'name': name,
        'price': price
    }

    flash('Added "{}" to cart.'.format(name), category='cart')

    if is_safe_url(request.referrer):
        return redirect(request.referrer)
    return redirect(url_for('main.products'))

@bp.route('/cart/update', methods=['POST'])
def update_cart():
    sku_id = request.form['sku']
    quantity = int(request.form['quantity'])

    if 'cart' not in session:
        session['cart'] = {}

    session['cart'][sku_id] = quantity
    if not quantity:
        del session['cart'][sku_id]

    flash('Cart updated.')

    if is_safe_url(request.referrer):
        return redirect(request.referrer)
    return redirect(url_for('main.products'))

@bp.route('/checkout')
def checkout():
    pass