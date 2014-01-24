#!/usr/bin/env python
# coding: utf8

from setuptools import setup, find_packages
import os

packages = find_packages()

def get_locals(filename):
    l = {}
    execfile(filename, {}, l)
    return l

metadata = get_locals(os.path.join('yadda', '_metadata.py'))

setup(
    name="yadda",
    version=metadata['version'],
    author=metadata['author'],
    author_email=metadata['author_email'],
    license=metadata['license'],
    url=metadata['url'],
    packages=find_packages()
    )