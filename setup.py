# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "riseml"
VERSION = "0.3.9"


REQUIRES = ["urllib3 >= 1.15", "six >= 1.10", "certifi", "python-dateutil"]

REQUIRES += ['pyyaml', 'requests', 'flask', 'flask-cors', 'jsonschema']

setup(
    name=NAME,
    version=VERSION,
    description="RiseML API client",
    author_email="contact@riseml.com",
    url="https://riseml.com",
    keywords=["RiseML"],
    entry_points={
        'console_scripts': [
            'riseml = riseml.__main__:main'
        ]
    },
    install_requires=REQUIRES,
    packages=find_packages(),
    include_package_data=True,
    long_description="""\
    
    """
)

