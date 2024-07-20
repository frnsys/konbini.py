import importlib
from flask import current_app

def get_shipping_rate(products, addr, shipper, **config):
    shipper_module = importlib.import_module('.' + shipper, 'konbini.shipping')
    return shipper_module.get_shipping_rate(products, addr, **config)

def buy_shipment(shipper, **kwargs):
    shipper_module = importlib.import_module('.' + shipper, 'konbini.shipping')
    return shipper_module.buy_shipment(**kwargs)

def shipment_exists(shipment_id, shipper):
    shipper_module = importlib.import_module('.' + shipper, 'konbini.shipping')
    return shipper_module.shipment_exists(shipment_id)

def confirmation_email_text(shipper, **kwargs):
    shipper_module = importlib.import_module('.' + shipper, 'konbini.shipping')
    return shipper_module.confirmation_email(**kwargs)
