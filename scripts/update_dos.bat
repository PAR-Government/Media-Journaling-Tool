del /Q build
del /Q dist
python setup.py sdist
pip install -e .
