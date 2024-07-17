import math
import stripe
import json
import requests
from flask import current_app
from konbini.util import send_email, check_state

url = current_app.config['RPI_URL']
auth = {'Authorization': current_app.config['RPI_AUTH_HEADER']}

def get_shipping_rate(products, addr, **config):
    """Estimate a shipping rate for a product.
    This does not actually purchase shipping, this is just to figure out
    how much to charge for it."""
    metadata_fields = ['sku', 'pagecount', 'guts_pdf', 'cover_pdf']
    order_items = []
    for p, q in products:
        missing_fields = [k for k in metadata_fields if k not in p.metadata]
        if missing_fields:
            new_order_recipients = current_app.config['NEW_ORDER_RECIPIENTS']
            send_email(new_order_recipients, "Missing product metadata", "admin_msg", message="Product {} is missing metadata fields in Stripe: {}".format(p.name, ", ".join(missing_fields)))

        order_items.append({
            "sku": p.metadata.get('sku'),
            "quantity": q,
            "pageCount": p.metadata.get('pagecount')
        })

    request_body = {
        "currency": "USD",
            "destination": {
                "name": addr['name'],
                "company": "",
                "address1": addr['address']['line1'],
                "city": addr['address']['city'],
                "state": check_state(addr['address']['state']),
                "postal": addr['address']['postal_code'],
                'country': addr['address']['country'],
                "phone": "",
                "email": ""
            },
            "orderItems": order_items
    }
    estimate_url = url + '/orders/shipping/estimate'

    response = requests.post(estimate_url, json=request_body, headers=auth)
    rates = response.json()

    # Get cheapest rate
    lowest_rate = rates[0]['price']

    # Convert to cents
    rpi_metadata, i = {}, 1
    for product, q in products:
        rpi_product_info = {x: product.metadata[x] for x in metadata_fields}
        rpi_product_info['quantity'], rpi_product_info['id']  = q, product.id
        rpi_product_info_string = json.dumps(rpi_product_info, default=lambda o: o.__dict__)
        rpi_metadata['rpi_product_' +str(i)] = rpi_product_info_string
        i += 1

    return math.ceil(float(lowest_rate) * 100), rpi_metadata

def buy_shipment(**kwargs):
    order_items, products, i = [], [], 1
    while kwargs.get('rpi_product_' + str(i)):
        product = json.loads(kwargs['rpi_product_'+str(i)])
        products.append(product)
        i += 1

    for p in products:
        prices = stripe.Price.list(limit=100, product=product['id'], active=True)['data']
        price = prices[0].unit_amount/100
        order_items.append({
            "sku": p['sku'],
            "quantity": p['quantity'],
            "retailPrice" : price,
            "pageCount": p['pagecount'],
            "product" : {
                "coverUrl": p['cover_pdf'],
                "gutsUrl": p['guts_pdf']
            }
        })

    request_body = {
        "currency":"USD",
        "shippingClassification":"economy",
        "webhookUrl":"",
        "destination": {
            "name": kwargs['name'],
            "company": "",
            "address1": kwargs['address_line1'],
            "address2": kwargs['address_line2'],
            "city": kwargs['address_city'],
            "state": check_state(kwargs['address_state']),
            "postal": kwargs['address_postal_code'],
            'country': kwargs['address_country'],
            "phone": "",
            "email": ""
        },
        "orderItems": order_items
    }
    create_url = url + '/orders/create'
    response = requests.post(create_url, json=request_body, headers=auth)
    return response.json()

def shipment_exists(shipment_id):
    exists_url = url + '/orders/' + shipment_id
    response = requests.get(exists_url, headers=auth)
    order = response.json()

    if order is not None and order.tracking_code:
        return True, order.tracker.public_url
    else:
        return False, None
