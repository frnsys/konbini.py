import math
import stripe
import easypost


def get_shipping_rate(products, addr, **config):
    """Estimate a shipping rate for a product.
    This does not actually purchase shipping, this is just to figure out
    how much to charge for it."""
    package_dimensions = [{
        k: float(p.metadata.get(k))
        for k in ['height', 'weight', 'length', 'width']
    } for p, _ in products]

    # ENH This should use some 3d bin packing algorithm
    # but for now just take the largest product volume
    # ENH this should take quantity into account
    dimensions = max(package_dimensions,
            key=lambda p: p['height'] * p['weight'] * p['length'])

    # We can at least sum the weights
    total_weight = sum(p['weight'] for p in package_dimensions)
    dimensions['weight'] = total_weight

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
        for (product, quantity), dims in zip(products, package_dimensions):
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

            # Create customs item. We are making a few assumptions here
            customs_item = easypost.CustomsItem.create(
                quantity=quantity,
                description=product.description,
                value=price,
                weight=dims['weight'],
                code=product.id,
                origin_country='US', # NOTE assumed to be US
                # hs_tariff_number # isn't required by easypost
            )
            customs_items.append(customs_item)
        customs_info = easypost.CustomsInfo.create(
            customs_items=customs_items,
            **config['KONBINI_CUSTOMS']
        )
        kwargs['customs_info'] = customs_info
    shipment = easypost.Shipment.create(**kwargs)

    # Get cheapest rate
    rate = min(float(r.rate) for r in shipment.rates)

    # Convert to cents
    return math.ceil(rate*100), {
        'shipment_id': shipment.id
    }


def buy_shipment(shipment_id, **kwargs):
    shipment = easypost.Shipment.retrieve(shipment_id)
    rate = min(shipment.rates, key=lambda r: float(r.rate))
    shipment.buy(rate=rate)
    return {
        'label_url': shipment.postage_label.label_url,
        'tracking_url': shipment.tracker.public_url
    }

def shipment_exists(shipment_id):
    shipment = easypost.Shipment.retrieve(shipment_id)
    if shipment is not None:
        return True, shipment.tracker.public_url
    else:
        return False, None