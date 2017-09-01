from setuptools import setup,find_packages

setup(name='maskgen',
      version_format='04.0810.{gitsha}',
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
      install_requires=['networkx>=1.11','pillow>=3.4.2','scikit-image','tkintertable','bitstring', 'awscli>=1.10.66', 'boto3>=1.3.1','numpy>=1.13.1','moviepy', 'h5py>=2.6.0','pydot>=1.2.3','graphviz>=0.5.1','pygraphviz>=1.3.1','rawpy>=0.7.0','cachetools','requests','matplotlib','pandas','wave'],
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
