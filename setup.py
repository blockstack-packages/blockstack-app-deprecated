#!/usr/bin/python

from setuptools import setup, find_packages

# to set __version__
exec(open('blockstack_app/version.py').read())

setup(
    name='blockstack-app',
    version=__version__,
    url='https://github.com/blockstack/blockstack-app',
    license='GPLv3',
    author='Blockstack.org',
    author_email='support@blockstack.org',
    description='Blockstack app runner',
    keywords='blockchain git crypography name key value store data',
    packages=find_packages(),
    download_url='https://github.com/blockstack/blockstack-app/archive/master.zip',
    zip_safe=False,
    include_package_data=True,
    scripts=['bin/blockstack-app'],
    install_requires=[
        'blockstack-client>=0.0.13.0',
        'blockstack-gpg>=0.0.1.0',
        'blockstack-file>=0.0.1.0'
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet',
        'Topic :: Security :: Cryptography',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
