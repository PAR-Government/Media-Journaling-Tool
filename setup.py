from setuptools import setup,find_packages

setup(name='maskgen',
      version='0.4.1',
      description='JT',
      url='http://github.com/rwgdrummer/maskgen',
      author='PAR Team',
      author_email='eric_robertson@partech.com',
      license='APL',
      packages=find_packages(exclude=["images", "plugins", "resources", "tests"]),
      install_requires=['networkx','pillow','scikit-image','tkintertable','bitstring', 'boto', 'boto3','numpy','moviepy', 'h5py','pydot','graphviz','pygraphviz','rawpy'],
      entry_points=
       {'gui_scripts': [
            'jtui = maskgen.MaskGenUI:main',
        ],
        'batch_scripts': [
               'jtproject = maskgen.batch.batch_project:main',
               'jtprocess = maskgen.batch.batch_process:main'
           ]
       },
      zip_safe=False)
