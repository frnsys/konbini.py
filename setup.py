from setuptools import setup

setup(
    name='konbini',
    version='0.1.0',
    description='simple web store for flask',
    url='https://github.com/frnsys/konbini',
    author='Francis Tseng',
    author_email='f@frnsys.com',
    license='GPLv3',
    include_package_data=True,
    packages=['konbini', 'flask_konbini', 'konbini.shipping'],
    install_requires=[
        'Flask==2.0.3',
        'Flask-WTF==1.0.1',
        'Flask-Mail==0.9.1',
        'stripe==2.48.0',
        'sentry-sdk==1.14.0',
        'easypost==3.6.3',
        'six==1.12.0',
        'pyusps==0.0.7',
        'country-list==0.1.3'
    ]
)
