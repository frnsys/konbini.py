import stripe

def get_products():
    return stripe.Product.list(limit=100, active=True, type='good')['data']

def get_plans():
    return stripe.Product.list(limit=100, active=True, type='service')['data']

def get_product(id):
    return stripe.Product.retrieve('prod_{}'.format(id))
