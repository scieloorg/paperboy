#coding: utf-8
#!/usr/bin/env python
from setuptools import setup, find_packages

install_requires = [
    "paramiko>=1.16.0"
]

tests_require = [
    "paramiko>=1.16.0"
]

setup(
    name="scielo_paperboy",
    version="0.6.3",
    description=u"Utilitary to send Images. PDF's, Translations and XML's from the local website to stanging and production servers",
    author="SciELO",
    author_email="scielo-dev@googlegroups.com",
    maintainer="Fabio Batalha",
    maintainer_email="fabio.batalha@scielo.org",
    license="BSD License",
    url="http://github.com/scieloorg/paperboy",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 2.7",
    ],
    dependency_links=[
    ],
    tests_require=tests_require,
    test_suite='tests',
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'paperboy=paperboy.send_to_server:main',
            'paperboy_delivery_to_server=paperboy.send_to_server:main',
            'paperboy_delivery_to_scielo=paperboy.send_to_scielo:main'
        ]
    }
)
