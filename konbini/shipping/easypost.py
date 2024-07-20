import math
import stripe
import json
import easypost
from flask import current_app
from konbini.util import send_email


def get_shipping_rate(products, addr, **config):
    """Estimate a shipping rate for a product.
    This does not actually purchase shipping, this is just to figure out
    how much to charge for it."""
    metadata_fields = ['height', 'weight', 'length', 'width']
    total_weight, total_length, total_width, total_height = 0, 0, 0, 0

    for p, q in products:
        missing_fields = [k for k in metadata_fields if k not in p.metadata]
        if missing_fields:
            new_order_recipients = current_app.config['NEW_ORDER_RECIPIENTS']
            send_email(new_order_recipients, "Missing product metadata", "admin_msg", message="Product {} is missing metadata fields in Stripe: {}".format(p.name, ", ".join(missing_fields)))

        # current bin packing algorithm assumes products are flat books, takes the largest width and heights
        # and calculates the height as a sum based on the assumption all books will be stacked flat on top of one another
        # find the width and height needed to fit all books flat
        length = max(float(p.metadata.get('length')),float(p.metadata.get('width')))
        width = min(float(p.metadata.get('length')),float(p.metadata.get('width')))
        if length > total_length:
            total_length = length
        if width > total_width:
            total_width = width

        # sum the heights
        total_height += float(p.metadata.get('height'))*q

        # sum the weights
        total_weight += float(p.metadata.get('weight'))*q

    dimensions = {'height':total_height,'width':total_width,'length':total_length,'weight':total_weight}

    kwargs = {
        'from_address': config['KONBINI_SHIPPING_FROM'],
        'to_address': {
            'name': addr['name'],
            'street1': addr['address']['line1'],
            'street2': addr['address'].get('line2'),
            'city': addr['address']['city'],
            'state': addr['address']['state'],
            'zip': addr['address']['postal_code'],
            'country': addr['address']['country']
        },
        'parcel': dimensions,
    }

    # https://www.easypost.com/customs-guide
    if addr['address']['country'] != 'US' and 'KONBINI_CUSTOMS' in config:
        customs_items = []
        for product, quantity in products:
            # ENH this can be improved
            # Grab first SKU to get price
            if product['type'] == 'good':
                skus = stripe.SKU.list(limit=100, product=product.id, active=True)['data']
                if skus:
                    price = skus[0].price/100 # cents to USD
                else:
                    prices = stripe.Price.list(limit=100, product=product.id, active=True)['data']
                    price = prices[0].unit_amount/100 # cents to USD
            else:
                prices = stripe.Price.list(limit=100, product=product.id, active=True)['data']
                price = prices[0].unit_amount/100 # cents to USD

            hs_tariff_number = product.metadata.get("hs_tariff_number")

            # Create customs item. We are making a few assumptions here
            customs_item = easypost.client.customs_item.create(
                quantity=quantity,
                description=product.description,
                value=price,
                weight=product.metadata.get('weight'),
                code=product.id,
                origin_country='US', # NOTE assumed to be US
                hs_tariff_number=hs_tariff_number
            )
            customs_items.append(customs_item)
        customs_info = easypost.client.customs_info.create(
            customs_items=customs_items,
            **config['KONBINI_CUSTOMS']
        )
        kwargs['customs_info'] = customs_info
    shipment = easypost.client.shipment.create(**kwargs)

    # Get cheapest rate
    lowest_rate = shipment.lowest_rate()

    # Convert to cents
    return math.ceil(float(lowest_rate.rate) * 100), {'easypost_shipment_id': shipment.id}

def buy_shipment(**kwargs):
    shipment = easypost.client.shipment.retrieve(kwargs['easypost_shipment_id'])
    shipment = easypost.client.shipment.buy(shipment.id, rate=shipment.lowest_rate())
    return {
        'label_url': shipment.postage_label.label_url,
        'tracking_url': shipment.tracker.public_url
    }

def shipment_exists(shipment_id):
    shipment = easypost.client.shipment.retrieve(shipment_id)
    if shipment is not None and shipment.tracking_code:
        return True, shipment.tracker.public_url
    else:
        return False, None
