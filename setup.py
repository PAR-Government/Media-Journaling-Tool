from setuptools import setup,find_packages

setup(name='maskgen',
      version='0.4.1',
      description='JT',
      url='http://github.com/rwgdrummer/maskgen',
      author='PAR Team',
      author_email='eric_robertson@partech.com',
      license='APL',

      packages=find_packages(exclude=["images", "plugins", "resources", "tests","wrapper_plugins"]),
      data_files=[('resources',['resources/operations.json','resources/software.csv','resources/project_properties.json']),
                  ('plugins/Custom',
                   ['plugins/Custom/GammaCorrection.json', 'plugins/Custom/GaussianBlur.json', 'plugins/Custom/LevelCorrection.json',
                    'plugins/Custom/Resize.json','plugins/Custom/OutputJpg.json','plugins/Custom/Sharpen.json','plugins/Custom/WaveletDenoise.json'
                    ])],
      install_requires=['networkx','pillow','scikit-image','tkintertable','bitstring', 'boto', 'boto3','numpy','moviepy', 'h5py','pydot','graphviz','pygraphviz','rawpy','cachetools'],
      entry_points=
       {'gui_scripts': [
            'jtuiw = maskgen.MaskGenUI:main',
        ],
        'console_scripts': [
               'jtproject = maskgen.batch.batch_project:main',
               'jtui = maskgen.MaskGenUI:main',
               'jtprocess = maskgen.batch.batch_process:main'
        ]
       },
      zip_safe=False)
