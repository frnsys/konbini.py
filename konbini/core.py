import stripe

def get_products():
    return stripe.Product.list(limit=100, active=True, type='good')['data']

def get_plans():
    return stripe.Product.list(limit=100, active=True, type='service')['data']

def get_product(id):
    return stripe.Product.retrieve('prod_{}'.format(id))

def get_customers(email):
    resp = stripe.Customer.list(email=email, limit=100)
    customers = resp['data']
    while resp.has_more:
        resp = stripe.Customer.list(email=email, starting_after=customers[-1], limit=100)
        customers += resp['data']
    return customers

