from .models import Product
from flask import Blueprint, render_template, redirect, request, session

bp = Blueprint('main', __name__)

@bp.route('/')
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@bp.route('/product/<slug>')
def product(slug):
    product = Product.query.get_or_404(slug)
    return render_template('product.html', product=product)

@bp.route('/plans')
def plans():
    # TODO get from stripe
    pass

@bp.route('cart', methods=['POST'])
def add_to_cart():
    sku_id = request.form['sku']

    if 'cart' not in session:
        session['cart'] = {}
    session['cart'][sku_id] = session['cart'].get(sku_id, 0) + 1

    return redirect(request.url)

@bp.route('cart/update', methods=['POST'])
def update_cart():
    sku_id = request.form['sku']
    quantity = request.form['quantity']

    if 'cart' not in session:
        session['cart'] = {}

    session['cart'][sku_id] = quantity
    if not quantity:
        del session['cart'][sku_id]

    return redirect(request.url)

@bp.route('checkout')
def checkout():
    pass