#!/usr/bin/env python

import setuptools

setuptools.setup(
    name = "callysto",
    version = "0.1b",
    packages = ["callysto"],
    package_dir = {"callysto": "lib"},
    requires = [
        "jupyter_core",
        "jupyter_client",
        "ipykernel",
        "ipywidgets",
        "six"])
