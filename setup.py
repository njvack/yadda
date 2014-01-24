#!/usr/bin/env python
# coding: utf8

from setuptools import setup, find_packages, Command
import os

packages = find_packages()

class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import sys
        import subprocess
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)

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
    packages=find_packages(),
    cmdclass = {'test': PyTest}
    )