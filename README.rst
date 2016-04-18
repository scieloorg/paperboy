Paperboy
========

Utilitário para envio de dados de sites locais SciELO para servidores SciELO. O 
utilitario permite o envio de bases para processamento, images, pdfs, traduções
e XML's.

Como instalar
=============

Linux
-----

pip install scielo-paperboy

Windows
-------

1. Instalar as seguintes dependência:

    paramiko 1.16.0 ou superior

    pycrypto 2.6.1 ou superior


2. Instalar Paperboy

    pip install scielo-paperboy

Como utilizar
=============

Com arquivo de configuração
---------------------------

Criar um arquivo de configuração utilizando o template config.ini-TEMPLATE

config.ini::

    [app:main]
    source_dir=/var/www/scielo
    cisis_dir=/var/www/scielo/proc/cisis
    scilista=/var/www/scielo/serial/scilista.lst
    destiny_dir=/var/www/scielo
    ssh_server=localhost
    ssh_port=22
    ssh_user=anonymous
    ssh_password=anonymous

Criar variável de ambiente indicando o arquivo de configuração

Linux

    export PAPERBOY_SETTINGS_FILE=config.ini

Windows

    set PAPERBOY_SETTINGS_FILE=config.ini

Utilitários disponíveis

* paperboy_delivery_to_server
* paperboy_delivery_to_scielo

Para ajuda

    paperboy_delivery_to_server --help
    
    paperboy_delivery_to_scielo --help

Para ativar módulo de compatibilidade de bases no utilitário **paperboy_delivery_to_server**. O modulo de compatibilidade
converte as bases de dados para que sejam compatíveis com o sistema operacional
de destino. Deve ser utilizado quando o objetivo é enviar bases do Windows para
o Linux ou o contrário.

    paperboy_delivery_to_server -m

Sem arquivo de configuração
---------------------------

Executar

    paperboy_delivery_to_scielo --help

    paperboy_delivery_to_server --help
