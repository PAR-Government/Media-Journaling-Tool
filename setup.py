from setuptools import setup,find_packages

setup(name='maskgen',
      version_format='04.0621.{gitsha}',
      setup_requires=['setuptools_maskgen_version'],
      description='JT',
      url='http://github.com/rwgdrummer/maskgen',
      author='PAR Team',
      author_email='eric_robertson@partech.com',
      license='APL',
      packages=find_packages(exclude=["images", "plugins", "resources", "tests","wrapper_plugins"]),
      data_files=[('resources',['resources/operations.json','resources/software.csv','resources/project_properties.json']),
		  ('icons',['icons/RedX.png','icons/audio.png','icons/rightarrow.png','icons/leftarrow.png','icons/subtract.png',
                   'icons/attach.png','icons/add.png','icons/question.png']),
                  ('plugins/Custom',
                   ['plugins/Custom/GammaCorrection.json', 'plugins/Custom/GaussianBlur.json', 'plugins/Custom/LevelCorrection.json',
                    'plugins/Custom/Resize.json','plugins/Custom/OutputJpg.json','plugins/Custom/Sharpen.json','plugins/Custom/WaveletDenoise.json'
                    ])],
      install_requires=['networkx','pillow','scikit-image','tkintertable','bitstring', 'awscli', 'boto3','numpy','moviepy', 'h5py','pydot','graphviz','pygraphviz','rawpy','cachetools','requests','matplotlib','pandas','awscli'],
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
