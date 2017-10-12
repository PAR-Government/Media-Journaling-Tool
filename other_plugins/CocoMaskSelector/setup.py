from setuptools import setup


setup(
    name='maskgen_coco',
    version='1.0.1',
    url='https://github.com/maskgen/other_plugins/CocoMaskSelector',
    author='rwgdrummer',
    author_email='rwgdrummer@gmail.com',
    description='COCO Integration',
    license='http://opensource.org/licenses/MIT',
    classifiers=[
        'Framework :: Setuptools Plugin',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
    ],
    py_modules=['maskgen_coco'],
    install_requires=[
        'pycocotools'
    ]
)
