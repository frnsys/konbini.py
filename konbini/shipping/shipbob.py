import math
import json
import uuid
import requests
from flask import current_app


def inventory_items_to_products(inventory_items):
    """There is a decent amount of overhead with
    these extra network calls, but ShipBob does not provide
    a more streamlined way (their entire API is horribly designed),
    so this is how we have to do it.
    """

    # Fetch products from the Default ShipBob channel
    product_data = {}
    default_channel_headers = {
        'shipbob_channel_id': current_app.config['SHIPBOB_DEFAULT_CHANNEL_ID'],
        'Authorization': 'bearer {}'.format(current_app.config['SHIPBOB_API_KEY'])
    }
    resp = requests.get('https://api.shipbob.com/1.0/product', headers=default_channel_headers)
    all_products = resp.json()
    for p in all_products:
        for item in p['fulfillable_inventory_items']:
            inv_id = item['id']
            product_data[inv_id] = {'sku': p['sku'], 'name': p['name']}

    # Fetch products from the store-specific ShipBob channel
    mapping = {}
    headers = {
        'shipbob_channel_id': current_app.config['SHIPBOB_CHANNEL_ID'],
        'Authorization': 'bearer {}'.format(current_app.config['SHIPBOB_API_KEY'])
    }
    resp = requests.get('https://api.shipbob.com/1.0/product', headers=headers)
    all_products = resp.json()
    for p in all_products:
        for item in p['fulfillable_inventory_items']:
            inv_id = item['id']
            mapping[inv_id] = p['id']

    products = []
    for item in inventory_items:
        try:
            product_id = mapping[item['id']]
        except KeyError:
            # Get the default product id and then create a new one
            # in the store channel
            data = product_data[item['id']]

            # Create the necessary product
            resp = requests.post('https://api.shipbob.com/1.0/product', json={
                'sku': data['sku'],
                'reference_id': data['sku'],
                'name': data['name']
            }, headers=headers)
            try:
                resp.raise_for_status()
            except:
                raise Exception('{} for {}: {}'.format(resp.status_code, resp.url, resp.content))
            product_id = resp.json()['id']
            mapping[item['id']] = product_id

            # raise Exception('No product found for inventory id "{}"'.format(item['id']))
        products.append({
            'id': product_id,
            'quantity': item['quantity']
        })
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
        raise Exception('{} for {}: {}'.format(resp.status_code, resp.url, resp.content))
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
    address = {'address': address}

    name = kwargs['name']
    products = inventory_items_to_products(products)
    rates = _get_shipping_rates(products, address)
    rate = min(rates, key=lambda r: r['estimated_price'])

    addr = {
        'address1': address['address']['line1'],
        'address2': address['address'].get('line2'),
        'city': address['address']['city'],
        'state': address['address']['state'],
        'zip_code': address['address']['postal_code'],
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
        raise Exception('{} for {}: {} (shipment_id: {})'.format(resp.status_code, resp.url, resp.content, shipment_id))

    # We may not get a tracking url right away
    data = resp.json()
    shipments = data['shipments']
    if shipments and shipments[0] is not None:
        tracking_data = shipments[0].get('tracking', None) or {}
        tracking_url = tracking_data.get('tracking_url')
    else:
        tracking_url = None
    return {
        'tracking_url': tracking_url,
    }


def shipment_exists(shipment_id):
    # Shipbob's API docs say this will filter by reference ids,
    # the endpoint actually just returns all orders...but
    # using this just in case they ever get around to fixing that.
    data = {'ReferenceIds': [shipment_id]}
    resp = requests.get('https://api.shipbob.com/1.0/order', json=data, headers={
        'shipbob_channel_id': current_app.config['SHIPBOB_CHANNEL_ID'],
        'Authorization': 'bearer {}'.format(current_app.config['SHIPBOB_API_KEY'])
    })
    orders = resp.json()
    matches = [order for order in orders if order['reference_id'] == shipment_id]
    if matches:
        order = matches[0]
        if order['shipments']:
            return True, order['shipments'][0]['tracking']
        else:
            return True, None
    else:
        return False, None
