#coding: utf-8
#!/usr/bin/env python
from setuptools import setup, find_packages

install_requires = []

tests_require = [
    "paramiko==1.16.0"
]

setup(
    name="paperboy",
    version="0.2.0",
    description="Utilitário para envio de Imagens, PDF's, Traducões e Bases de sites locais SciELO para os servidores de homologação e produção",
    author="SciELO",
    author_email="scielo-dev@googlegroups.com",
    maintainer="Fabio Batalha",
    maintainer_email="fabio.batalha@scielo.org",
    url="http://github.com/scieloorg/processing",
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
            'paperboy=paperboy:main'
        ]
    }
)
