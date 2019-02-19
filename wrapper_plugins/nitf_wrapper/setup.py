from setuptools import setup,find_packages

setup(name='nitf_wrapper',
      version='0.0.1',
      description='nitf_wrapper plugins',
      url='http://github.com/rwgdrummer/maskgen_plugins/nitf_wrapper',
      author='PAR Team',
      author_email='eric_robertson@partech.com',
      license='APL',
      packages=find_packages(exclude=["tests"]),
      install_requires=['GDAL'],
      entry_points=
       {'maskgen_image': [
            'ntf = nitf_wrapper.opener:openNTFFile',
            'nitf = nitf_wrapper.opener:openNTFFile'
        ]
       },
      zip_safe=False)
