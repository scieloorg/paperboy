Paperboy Dockerizado
====================
SciELO utility created to send data (Images, PDFs, Databases and XML's translations) to homologation server to process the SciELO's databases and save pdfs and images files in the right directory. 

How to use this image
=====================
To run this images as container is important to create a config.ini volume which is set up variables that will be used by papeboy service. Also, it is important to mount SciELO Metodology Web Directory which will be used to send Images, PDFs and Bases to the target server.

Setting up config.ini file
--------------------------
```
[app:main]

## Full path to the source directory where the SciELO site is installed. It must 
## contains the directories proc, bases, htdocs, cgi-bin, serial.
source_dir=/var/www/scielo

## Full path to the CISIS utilitaries. It is usually installed on the directory
## proc/cisis of the SciELO Site.
cisis_dir=/var/www/scielo/proc/cisis

## Full path to the scilista.lst file. It is usually available at the directory
## and file serial/scilista.lst
scilista=/var/www/scielo/serial/scilista.lst

## Full path to the destiny folder in the server side. It is usually the path
## to the SciELO Site in the server. When sending data to SciELO is must be 
## commented or empty on the FTP will login the user to the correct path.
destiny_dir=/var/www/scielo

## FTP or SFTP credentials
## The protocol will be defined by the server_type ['ftp', 'sftp']
server=<target ip address>
server_type=<server type: sftp or ftp>
port=<server port number>
user=<server username>
password=<server user's password>
```
Please fill up with right server credentials. If your server doesn't have ftp use sftp (ssh way).

Starting Paperboy instance
--------------------------
```
docker run -it --restart unless-stopped \
       --env PAPERBOY_SETTINGS_FILE=/app/config.ini
       -v $(PWD)/config.ini:/app/config.ini
       -v $(PWD)/scielo:/var/www/scielo
       scieloorg/paperboy 
       paperboy_delivery_to_server -m
```

Observation: The files only will be sent if the config.ini is setting properly.
