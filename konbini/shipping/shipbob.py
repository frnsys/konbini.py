import math
import uuid
import requests
from flask import current_app


def get_shipping_rates(products, addr):
    """
    <https://developer.shipbob.com/api-docs/#tag/Orders/paths/~1order~1estimate/post>
    """
    address = {
        'address1': addr['address']['line1'],
        'address2': addr['address'].get('line2'),
        'city': addr['address']['city'],
        'state': addr['address']['state'],
        'zip': addr['address']['postal_code'],
        'country': addr['address']['country']
    }

    data = {
        'address': address,
        'products': products,
    }
    resp = requests.post('https://api.shipbob.com/1.0/order/estimate', json=data, headers={
        'shipbob_channel_id': current_app.config['SHIPBOB_CHANNEL_ID'],
        'Authorization': 'bearer {}'.format(current_app.config['SHIPBOB_API_KEY'])
    })
    try:
        resp.raise_for_status()
    except:
        raise Exception('{} for {}: {}'.format(resp.status_code, resp.url, resp.json()))
    data = resp.json()
    return data['estimates']


def get_shipping_rate(products, addr, **config):
    shipped_products = []
    for (product, quantity) in products:
        shipbob_id = product.metadata.get('shipbob_inventory_id')
        if shipbob_id is None: raise Exception('Missing shipbob_inventory_id metadata field for Stripe product')
        shipped_products.append({
            'id': int(shipbob_id),
            'quantity': quantity
        })

    rates = get_shipping_rates(shipped_products, addr)

    # Get cheapest rate
    rate = min(r['estimated_price'] for r in rates)

    # Convert to cents
    rate = math.ceil(rate*100)

    # Create shipment id
    shipment_id = str(uuid.uuid4()).replace('-', '')
    return rate, {
        'shipment_id': shipment_id,
        'address': addr,
        'products': shipped_products
    }


def buy_shipment(shipment_id, products, address):
    name = address['name']
    rates = get_shipping_rates(products, address)
    rate = min(rates, key=lambda r: r['estimated_price'])

    addr = {
        'address1': address['address']['line1'],
        'address2': address['address'].get('line2'),
        'city': address['address']['city'],
        'state': address['address']['state'],
        'zip': address['address']['postal_code'],
        'country': address['address']['country']
    }

    data = {
        'shipping_method': rate['shipping_method'],
        'recipient': {
            'name': name,
            'address': addr,
        },
        'products': products, # products already properly formatted
        'reference_id': shipment_id

    }
    resp = requests.post('https://api.shipbob.com/1.0/order', json=data, headers={
        'shipbob_channel_id': current_app.config['SHIPBOB_CHANNEL_ID'],
        'Authorization': 'bearer {}'.format(current_app.config['SHIPBOB_API_KEY'])
    })
    try:
        resp.raise_for_status()
    except:
        raise Exception('{} for {}: {}'.format(resp.status_code, resp.url, resp.json()))

    data = resp.json()
    tracking_url = data['shipments'][0]['tracking']['tracking_url']
    return {
        'tracking_url': tracking_url,
    }
