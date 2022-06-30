from setuptools import setup, find_packages
import os

this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = ''.join(f.readlines())

setup(
    name='dsw-tdk',
    version='3.13.0',
    keywords='dsw template toolkit jinja documents',
    description='Data Stewardship Wizard Template Development Toolkit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Marek Suchánek',
    author_email='marek.suchanek@ds-wizard.org',
    url='https://github.com/ds-wizard/dsw-tdk',
    license='Apache-2.0',
    packages=find_packages(),
    package_data={
        'dsw_tdk': [
            'templates/*.j2',
        ]
    },
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
        'multidict',
        'pathspec',
        'python-dotenv',
        'python-slugify',
        'watchgod',
    ],
    python_requires='>=3.6, <4',
    setup_requires=[
        'pytest-runner',
        'wheel',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Topic :: Internet :: WWW/HTTP :: Site Management',
        'Topic :: Utilities',
    ],
    zip_safe=False,
)
