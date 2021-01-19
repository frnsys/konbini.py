import importlib
from flask import current_app

def get_shipping_rate(products, addr, **config):
    shipper = importlib.import_module(current_app['SHIPPER'])
    return shipper.get_shipping_rate(products, addr, **config)

def buy_shipment(shipment_id, **kwargs):
    shipper = importlib.import_module(current_app['SHIPPER'])
    return shipper.buy_shipment(shipment_id, **kwargs)
