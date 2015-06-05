#!/usr/bin/env python

from setuptools import setup, find_packages


version = '0.1.0'

setup(
    name='quickbooks-desktop-worker',
    version=version,
    description="Receive and return quickbooks requests and responses through celery task queue",
    author='SendOutCards',
    packages=find_packages(exclude=['*.tests']),
    platforms=["any"],
    zip_safe=False,
    install_requires=[
        "requests",
        "celery==3.1.18",
        "lxml",
        "win32com"
        ],
)
