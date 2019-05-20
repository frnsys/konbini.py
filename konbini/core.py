import stripe

def get_products():
    return stripe.Product.list(limit=100, active=True, type='good')['data']

def get_plans():
    return stripe.Product.list(limit=100, active=True, type='service')['data']
