from setuptools import setup,find_packages

setup(name='rawphoto_wrapper',
      version='0.0.1',
      description='rawphoto_wrapper plugins',
      url='http://github.com/rwgdrummer/maskgen_plugins/rawphoto_wrapper',
      author='PAR Team',
      author_email='eric_robertson@partech.com',
      license='APL',
      packages=find_packages(exclude=["tests"]),
      install_requires=['rawkit'],
      entry_points=
       {'maskgen_image': [
            'cr2 = rawphoto_wrapper.opener:openRawFile'
        ]
       },
      zip_safe=False)
