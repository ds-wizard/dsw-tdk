from setuptools import setup, find_packages
import os

this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = ''.join(f.readlines())

setup(
    name='dsw-tdk',
    version='2.7.0-alpha.1',
    keywords='dsw template toolkit jinja documents',
    description='Data Stewardship Wizard Template Development Toolkit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Marek Suchánek',
    author_email='marek.suchanek@ds-wizard.org',
    license='Apache-2.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'dsw-tdk = dsw_tdk:main',
        ]
    },
    install_requires=[
        'aiohttp',
        'click',
        'colorama',
        'humanize',
        'Jinja2',
        'pathspec',
        'python-dotenv',
        'python-slugify',
        'watchgod',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
    classifiers=[
        'Framework :: AsyncIO',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
    ],
)
