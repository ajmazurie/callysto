#!/usr/bin/env python

import setuptools

setuptools.setup(
    name = "demo_sql_kernel",
    version = "0.0",
    packages = [
        "demo_sql_kernel"],
    package_dir = {
        "demo_sql_kernel": "lib"},
    install_requires = [
        "callysto",
        "sqlparse"])
