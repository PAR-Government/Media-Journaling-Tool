from setuptools import setup,find_packages

setup(name='jpeg2000_wrapper',
      version='0.0.1',
      description='jpeg2000_wrapper plugins',
      url='http://github.com/rwgdrummer/maskgen_plugins/jpeg2000_wrapper',
      author='PAR Team',
      author_email='eric_robertson@partech.com',
      license='APL',
      packages=find_packages(exclude=["tests"]),
      install_requires=['glymur'],
      entry_points=
       {'maskgen_image': [
            'jp2 = jpeg2000_wrapper.opener:openJPeg2000File',
            'jpx = jpeg2000_wrapper.opener:openJPeg2000File'
        ],
        'maskgen_image_writer': [
            'jp2 = jpeg2000_wrapper.opener:writeJPeg2000File',
            'jpx = jpeg2000_wrapper.opener:writeJPeg2000File'
        ]
       },
      zip_safe=False)
