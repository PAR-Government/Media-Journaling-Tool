import os

from setuptools import setup, find_packages

setup(name='maskgen',
      version_format='0.6.0227.{gitsha}',
      setup_requires=['setuptools_maskgen_version'],
      description='JT',
      url='http://github.com/rwgdrummer/maskgen',
      author='PAR Team',
      author_email='eric_robertson@partech.com',
      license='APL',
      packages=find_packages(exclude=["images", "plugins", "resources", "tests", "wrapper_plugins"]),
      data_files=[
          ('resources', ['resources/operations.json', 'resources/software.csv', 'resources/project_properties.json']),
          ('icons',
           [os.path.join('icons', x) for x in os.listdir('icons') if os.path.splitext(x)[1] in ['.png', '.jpg']]),
          ('plugins/Custom',
           [os.path.join('plugins/Custom', x) for x in os.listdir('plugins/Custom') if
            os.path.splitext(x)[1] in ['.json']])],
      install_requires=['networkx==1.11', 'pillow>=3.4.2', 'scikit-image>=0.12.3,<0.14', 'tkintertable==1.2',
                        'bitstring', 'awscli>=1.10.66', 'boto3>=1.3.1', 'numpy>=1.13.1,<1.16.0', 'h5py>=2.6.0',
                        'pydot>=1.2.3,<1.4.0', 'graphviz>=0.8', 'pygraphviz>=1.3.1', 'rawpy>=0.10.1', 'cachetools',
                        'requests', 'matplotlib>=2.0.0,<=2.3', 'pandas>=0.19.2,<0.21.0', 'wave', 'pypng', 'numpngw', 
                        'shapely', 'wrapt', 'PyPDF2>=1.26.0', 'httplib2>=0.11.3', 'psutil','pydub'],
      # temp removed pyssl require
      test_requires=['python-pptx'],
      entry_points=
      {'gui_scripts': [
          'jtuiw = maskgen.ui.MaskGenUI:main',
      ],
          'console_scripts': [
              'jtproject = maskgen.batch.batch_project:main',
              'jtbatch = maskgen.batch.batch_processes:main',
              'jtui = maskgen.ui.MaskGenUI:main',
              'jtprocess = maskgen.batch.batch_process:main'
          ]
      },
      zip_safe=False)
