from setuptools import setup


setup(
    name='setuptools_maskgen_version',
    version='1.0.1',
    url='https://github.com/maskgen/setuptools-version',
    author='rwgdrummer',
    author_email='rwgdrummer@gmail.com',
    description='Automatically set package version from repo.',
    license='http://opensource.org/licenses/MIT',
    classifiers=[
        'Framework :: Setuptools Plugin',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
    ],
    py_modules=['setuptools_maskgen_version'],
    install_requires=[
        'setuptools >= 8.0','requests'
    ],
    entry_points="""
        [distutils.setup_keywords]
        version_format = setuptools_maskgen_version:validate_version_format
    """,
)
