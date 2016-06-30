#!/usr/bin/env python

import glob
import setuptools

__NAME__ = "callysto"
__VERSION__ = "0.2.3"

setuptools.setup(
    name = __NAME__,
    version = __VERSION__,
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

    # package requirements
    install_requires = [
        "docopt",
        "enum34",
        "future",
        "html",
        "inflect",
        "jupyter",
        "pydotplus",
        "pygraphviz",
        "six"],

    # package metadata
    url = "https://github.com/ajmazurie/" + __NAME__,
    download_url = (
        "https://github.com/ajmazurie/"
        "%s/archive/%s.zip" % (__NAME__, __VERSION__)),

    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: IPython",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7"])
