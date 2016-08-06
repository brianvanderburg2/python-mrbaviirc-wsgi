#!/usr/bin/env python

from setuptools import setup, find_packages

metadata = {}
with open("mrbaviirc/__init__.py") as handle:
    exec(handle.read(), metadata)

setup(
    name="mrbaviirc",
    version=metadata["__version__"],
    description=metadata["__doc__"].strip(),
    author=metadata["__author__"],
    packages=find_packages()
)
