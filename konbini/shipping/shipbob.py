import math
import json
import uuid
import requests
from flask import current_app


def inventory_items_to_products(inventory_items):
    """This makes the assumption that there is a one-to-one mapping
    between inventory items and products. This assumption should hold
    because the only way to create additional products for a given
    inventory item is through the API, which we aren't doing.
    We dynamically get this instead of just storing product ids
    on the Stripe products' metadata bceause there is no way
    to get product ids from the dashboard. The only way is through the API
    and I don't want to have to re-fetch product ids every time someone
    adds a new product to Stripe."""
    mapping = {}
    resp = requests.get('https://api.shipbob.com/1.0/product', headers={
        'shipbob_channel_id': current_app.config['SHIPBOB_CHANNEL_ID'],
        'Authorization': 'bearer {}'.format(current_app.config['SHIPBOB_API_KEY'])
    })
    all_products = resp.json()
    for p in all_products:
        for item in p['fulfillable_inventory_items']:
            inv_id = item['id']
            mapping[inv_id] = p['id']

    products = []
    for item in inventory_items:
        try:
            products.append({
                'id': mapping[item['id']],
                'quantity': item['quantity']
            })
        except KeyError:
            raise Exception('No product found for inventory id "{}"'.format(item['id']))
    return products


def _get_shipping_rates(products, addr):
    """
    <https://developer.shipbob.com/api-docs/#tag/Orders/paths/~1order~1estimate/post>
    """
    address = {
        'address1': addr['address']['line1'],
        'address2': addr['address'].get('line2'),
        'city': addr['address']['city'],
        'state': addr['address']['state'],
        'zip_code': addr['address']['postal_code'],
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
    shipped_inventory = []
    for (product, quantity) in products:
        shipbob_id = product.metadata.get('shipbob_inventory_id')
        if shipbob_id is None: raise Exception('Missing shipbob_inventory_id metadata field for Stripe product')
        shipped_inventory.append({
            'id': int(shipbob_id),
            'quantity': quantity
        })

    shipped_products = inventory_items_to_products(shipped_inventory)
    rates = _get_shipping_rates(shipped_products, addr)

    # Get cheapest rate
    rate = min(r['estimated_price'] for r in rates)

    # Convert to cents
    rate = math.ceil(rate*100)

    # Create shipment id
    shipment_id = str(uuid.uuid4()).replace('-', '')
    return rate, {
        'shipment_id': shipment_id,

        # keep as inventory, will be converted again later
        'products': json.dumps(shipped_inventory)
    }


def buy_shipment(shipment_id, **kwargs):
    products = json.loads(kwargs['products'])

    # Reconstruct the address from the order metadata
    address = {}
    for key, val in kwargs.items():
        if key.startswith('address_'):
            _, k = key.split('_', 1)
            address[k] = val

    name = kwargs['name']
    products = inventory_items_to_products(products)
    rates = _get_shipping_rates(products, address)
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
