from setuptools import setup,find_packages

setup(name='hptool',
      version='0.5',
      description='HP data processing',
      url='http://github.com/rwgdrummer/maskgen',
      author='PAR Team',
      author_email='andrew_smith@partech.com',
      license='APL',

      packages = find_packages(),
      package_data = {'':['*.json', '*.csv', '*.png', '*.txt']},
      install_requires=['pandas','pandastable','pillow', 'requests', 'boto3'],
      entry_points=
       {'gui_scripts': [
            'hpguiw = hp.hpgui:main',
        ],
        'console_scripts': [
            'hpgui = hp.hpgui:main',
        ]
       },
      zip_safe=False)
