from setuptools import setup

setup(name='maskgen',
      version='0.1',
      description='JT',
      url='http://github.com/rwgdrummer/maskgen',
      author='PAR Team',
      author_email='eric_robertson@partech.com',
      license='APL',
      packages=['maskgen'],
      install_requires=['networkx','pillow','scikit-image','tkintertable','bitstring','boto3','numpy','moviepy'],
      zip_safe=False)
