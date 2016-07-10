#!/usr/bin/env python


from setuptools import setup, find_packages

from setuptools.command.install_egg_info import install_egg_info
from setuptools.command.install_lib import install_lib

# Prevent from creating the namespace hack .pth
# Why? Because when this .pth is used, only packages in the same namespace that
# are added the same way, with this hack, are found, instead of any on sys.path
def dummy(self):
    pass
install_egg_info.install_namespaces = dummy

# Force installation of __init__.py both for python 2 and 3.  For Python 2
# this is required since it doesn't support implicit namespaces.  For Python 3
# this is needed because the implicit search breaks once an __init__.py is
# found, for example on the project directory
_gen_exclusion_paths = install_lib._gen_exclusion_paths
def dummy2(self):
    for i in _gen_exclusion_paths():
        if i == "__init__.py":
            continue
        yield i
install_lib._gen_exclusion_paths = dummy2

setup(
    name="mrbavii",
    version="0.1",
    description="Mr. Brian Allen Vanderburg II Reusable Code",
    author = "Brian Allen Vanderburg II",
    packages=find_packages(),
    namespace_packages=["mrbavii"]
)
