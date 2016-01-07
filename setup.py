# -*- coding:utf-8 -*-
from setuptools import setup, find_packages
setup(
    name = "gTornado",
    version = "0.1",
    packages = find_packages(),
    install_requires = ['tornado>=4.3', 'greenlet', "pymemcache>=1.3.5", "PyMySQL>=0.6.7"],
    author = "alexzhang",
    author_email = "alex8224@gmail.com",
    description = "gTornado add greenify support to tornado. inspired by motor and gevent",
    license = "MIT",
    keywords = "tornado greenify async",
    url = "https://github.com/alex8224/gTornado",
)

