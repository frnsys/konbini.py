import stripe

def get_products():
    return stripe.Product.list(expand=['data.default_price'], limit=100, active=True)['data']

def get_product(id):
    return stripe.Product.retrieve('prod_{}'.format(id), expand=['default_price'])

def get_customers(email):
    resp = stripe.Customer.list(email=email, limit=100)
    customers = resp['data']
    while resp.has_more:
        resp = stripe.Customer.list(email=email, starting_after=customers[-1], limit=100)
        customers += resp['data']
    return customers
