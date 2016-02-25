#!/usr/bin/env python

import glob
import setuptools

setuptools.setup(
    name = "callysto",
    version = "0.1b3",
    packages = [
        "callysto",
        "callysto.renderers"],
    package_dir = {
        "callysto": "lib"},
    scripts = glob.glob("bin/*"),
    install_requires = [
        "docopt",
        "enum34",
        "future",
        "html",
        "inflect",
        "ipykernel",
        "ipywidgets",
        "jupyter_client",
        "jupyter_core",
        "six"])
