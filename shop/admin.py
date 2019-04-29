import os
import config
from . import forms
from .datastore import db
from slugify import slugify
from .models import Product, SKU
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, flash, url_for, jsonify

bp = Blueprint('admin', __name__, url_prefix='/admin')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in forms.ALLOWED_EXTENSIONS


@bp.route('/')
def products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)


@bp.route('/product', defaults={'id': None}, methods=['GET', 'POST'])
@bp.route('/product/<int:id>', methods=['GET', 'POST'])
def product(id):
    if id is None:
        product = Product()
        form = forms.PostForm()
    else:
        product = Product.query.get_or_404(id)
        form = forms.PostForm(obj=product)

    if form.validate_on_submit():
        form.populate_obj(product)
        if not product.slug:
            product.slug = slugify(product.name)
        db.session.add(product)
        db.session.commit()
        flash('Product updated.')
    return render_template('admin/product.html', product=product, form=form)


@bp.route('/product/<int:product_id>/skus', defaults={'id': None}, methods=['GET', 'POST'])
@bp.route('/product/<int:product_id>/skus/<int:id>', methods=['GET', 'POST'])
def sku(product_id, id):
    if id is None:
        sku = SKU(product_id=product_id)
        form = forms.SKUForm()
    else:
        sku = SKU.query.get_or_404(id)
        form = forms.SKUForm(obj=sku)

    if form.validate_on_submit():
        form.populate_obj(sku)
        if not sku.slug:
            sku.slug = slugify(sku.name)
        db.session.add(sku)
        db.session.commit()
        flash('SKU updated.')

    image_form = forms.ImageForm()
    return render_template('admin/sku.html', product=product, sku=sku, form=form, image_form=image_form)

@bp.route('/product/<int:product_id>/skus/<int:id>/image', methods=['POST', 'DELETE'])
def image(product_id, id):
    sku = SKU.query.get_or_404(id)

    if request.method == 'POST':
        form = forms.ImageForm()
        if form.validate_on_submit():
            file = request.files[form.file.name]
            if file.filename == '':
                flash('No selected file.')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                savepath = os.path.join(config.UPLOAD_FOLDER, filename)
                file.save(savepath)
                sku.images.append(filename)
                db.session.add(sku)
                db.session.commit()
                flash('Image uploaded.')

    elif request.method == 'DELETE':
        data = request.get_json()
        sku.images = [im for im in sku.images if im != data['filename']]
        db.session.add(sku)
        db.session.commit()
        return jsonify(success=True)

    return redirect(url_for('admin.sku', product_id=product_id, id=id))
