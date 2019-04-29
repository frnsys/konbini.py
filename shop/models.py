from .datastore import db
from flask import url_for
from datetime import datetime


class Product(db.Model):
    id                      = db.Column(db.Integer(), primary_key=True)
    slug                    = db.Column(db.Unicode(), unique=True)
    name                    = db.Column(db.Unicode())
    price                   = db.Column(db.Integer()) # cents
    desc                    = db.Column(db.Unicode())
    published               = db.Column(db.Boolean(), default=False)
    created_at              = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at              = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def price_str(self):
        return '${}'.format(self.price/100)

    @property
    def image(self):
        if self.skus:
            return self.skus[0].image
        return url_for('static', filename='none.png')


class SKU(db.Model):
    id                      = db.Column(db.Integer(), primary_key=True)
    slug                    = db.Column(db.Unicode())
    name                    = db.Column(db.Unicode())
    images                  = db.Column(db.Unicode())
    stock                   = db.Column(db.Integer())
    created_at              = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at              = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    product_id              = db.Column(db.Integer, db.ForeignKey('product.id'))
    product                 = db.relationship('Product',
                                              uselist=False,
                                              backref=db.backref('skus', lazy='dynamic'))

    @property
    def image(self):
        if self.images:
            return url_for('main.uploads', filename=self.images[0])
        return url_for('static', filename='none.png')


class Order(db.Model):
    id                      = db.Column(db.Integer(), primary_key=True)
    customer_id             = db.Column(db.String())
    created_at              = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at              = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderItem(db.Model):
    id                      = db.Column(db.Integer(), primary_key=True)
    quantity                = db.Column(db.Integer())
    price                   = db.Column(db.Integer()) # cents
    order_id                = db.Column(db.Integer, db.ForeignKey('order.id'))
    order                   = db.relationship('Order',
                                              uselist=False,
                                              backref=db.backref('items', lazy='dynamic'))
    sku_id                  = db.Column(db.Integer, db.ForeignKey('sku.id'))
    sku                     = db.relationship('SKU',
                                              uselist=False,
                                              backref=db.backref('orders', lazy='dynamic'))


class Subscription(db.Model):
    id                      = db.Column(db.Integer(), primary_key=True)
    customer_id             = db.Column(db.String())
    subscription_id         = db.Column(db.String())
    created_at              = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at              = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
