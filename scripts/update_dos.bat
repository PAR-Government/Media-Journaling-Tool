del /Q /S /F build
del /Q /S /F dist
python setup.py sdist
pip install -e .
