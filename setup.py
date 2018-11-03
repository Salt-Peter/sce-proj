# http://flask.pocoo.org/docs/1.0/patterns/packages/
from setuptools import setup

setup(
    name='app',
    packages=['app'],
    include_package_data=True,
    install_requires=[
        'flask',
    ],
)
