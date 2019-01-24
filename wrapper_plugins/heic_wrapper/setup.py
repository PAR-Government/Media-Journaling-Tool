from setuptools import setup,find_packages

setup(name='heic_wrapper',
      version='0.0.1',
      description='heic_wrapper plugins',
      url='http://github.com/rwgdrummer/maskgen_plugins/heic_wrapper',
      author='PAR Team',
      author_email='luke_macri@partech.com',
      license='APL',
      packages=find_packages(exclude=["tests"]),
      install_requires=['wand'],
      entry_points=
      {'maskgen_image': [
          'heic = heic_wrapper.opener:open_heic',
          'heif = heic_wrapper.opener:open_heic'
      ]
      },
      zip_safe=False)