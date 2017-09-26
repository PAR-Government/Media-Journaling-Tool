#!/bin/bash
rm -rf build
rm -rf dist
python setup.py sdist
pip install -e .
