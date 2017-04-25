from setuptools import setup,find_packages

setup(name='trello_plugin',
      version='0.0.1',
      description='maskgen trello plugins',
      url='http://github.com/rwgdrummer/trello_plugin/trello_plugin',
      author='PAR Team',
      author_email='eric_robertson@partech.com',
      license='APL',
      packages=find_packages(exclude=["tests"]),
      data_files=[('resources',['resources/trello.json'])],
      entry_points=
       {'maskgen_notifiers': [
            'trello_plugin = trello_plugin.trello:factory'
        ]
       },
      zip_safe=False)

