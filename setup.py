#!/usr/bin/env python

import glob
import setuptools

setuptools.setup(
    name = "callysto",
    version = "0.2",
    description = (
        "Framework to create domain-specific "
        "kernels for the Jupyter platform"),

    author = "Aurelien Mazurie",
    author_email = "ajmazurie@oenone.net",

    # package content
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
        "six"],

    # package metadata
    url = "https://github.com/ajmazurie/callysto",
    download_url = "https://github.com/ajmazurie/callysto/archive/0.2.zip",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: IPython",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7"])
