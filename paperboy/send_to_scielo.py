# coding: utf-8
import argparse
import logging
import logging.config
import os
import subprocess

from paperboy.utils import settings
from paperboy.communicator import SFTP, FTP

logger = logging.getLogger(__name__)

LOGGING = {
    'version': 1,
    'formatters': {
        'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'NOTSET',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'ERROR'
        },
        'paperboy': {
            'handlers': ['console'],
            'level': 'INFO'
        }
    }
}


def _config_logging(logging_level='INFO'):

    LOGGING['loggers']['paperboy']['level'] = logging_level

    logging.config.dictConfig(LOGGING)


def make_iso(mst_input, iso_output, cisis_dir=None, fltr=None, proc=None):

    logger.info(u'Making iso for %s', mst_input)

    status = '1'  # erro de acordo com stdout do CISIS

    command = [remove_last_slash(cisis_dir) + u'/mx' if cisis_dir else u'mx']
    command.append(mst_input)
    if fltr:
        command.append(u'btell=0')
        command.append(fltr)
    if proc:
        command.append(proc)
    command.append(u'iso=%s' % (iso_output))
    command.append(u'-all')
    command.append(u'now')

    logger.debug(u'Running: %s', u' '.join(command))
    try:
        status = subprocess.call(command)
    except OSError:
        logger.error(u'Error while running mx, check if the command is available on the syspath, or the CISIS path was correctly indicated in the config file')

    if str(status) == '0':
        logger.debug(u'ISO %s creation done for %s', iso_output, mst_input)
        return True

    if str(status) == '1':
        logger.error(u'ISO creation did not work for %s', mst_input)
        return False

    return False


def make_section_catalog_report(source_dir, cisis_dir):

    logger.info(u'Making report static_section_catalog.txt')

    command = u"""mkdir -p %s/bases/reports; %s/mx %s/bases/issue/issue btell=0 "pft=if p(v49) then (v35[1],v65[1]*0.4,s(f(val(s(v36[1]*4.3))+10000,2,0))*1.4,'|',v49^l,'|',v49^c,'|',v49^t,/) fi" lw=0 -all now > %s/bases/reports/static_section_catalog.txt""" % (
        source_dir,
        cisis_dir,
        source_dir,
        source_dir,
    )

    logger.debug(u'Running: %s', command)

    try:
        status = subprocess.Popen(command, shell=True)
        status.wait()
    except OSError:
        logger.error(u'Error while creating report, static_section_catalog.txt was not updated')

    logger.debug(u'Report static_section_catalog.txt done')


def make_static_file_report(source_dir, report):

    extension_name = 'htm' if report == 'translation' else report
    report_name = 'html' if report == 'translation' else report

    logger.info(u'Making report static_%s_files.txt', report_name)

    command = u'mkdir -p %s/bases/%s; mkdir -p %s/bases/reports; cd %s/bases/%s; find . -name "*.%s*" > %s/bases/reports/static_%s_files.txt' %(
        source_dir,
        report,
        source_dir,
        source_dir,
        report,
        extension_name,
        source_dir,
        report_name
    )

    logger.debug(u'Running: %s', command)
    try:
        status = subprocess.Popen(command, shell=True)
        status.wait()
    except OSError:
        logger.error(u'Error while creating report, static_%s_files.txt was not updated', report_name)

    logger.debug(u'Report static_%s_files.txt done', report_name)


def remove_last_slash(path):
    path = path.replace('\\', '/')

    try:
        return path[:-1] if path[-1] == '/' else path
    except IndexError:
        return path


class Delivery(object):

    def __init__(self, source_type, cisis_dir, source_dir, destiny_dir, server,
                 port, user, password):

        self.source_type = source_type
        self.cisis_dir = remove_last_slash(cisis_dir)
        self.source_dir = remove_last_slash(source_dir)
        self.destiny_dir = remove_last_slash(destiny_dir)
        if str(port) == u'22':
            self.client = SFTP(server, int(port), user, password)
        elif str(port) == u'21':
            self.client = FTP(server, int(port), user, password)
        else:
            raise TypeError(u'port must be 21 for ftp or 22 for sftp')

    def _local_remove(self, path):

        logger.info(u'Removing temporary file (%s)', path)

        try:
            os.remove(path)
            logger.debug(u'Temporary has being file removed (%s)', path)
        except OSError as e:
            logger.error(
                u'Fail while removing temporary file (%s): %s',
                path,
                e.strerror
            )

    def send_isos(self):
        """
        This method will prepare and send article, issue, issues and bib4cit
        iso files to SciELO.

        Those files are used to produce bibliometric and site usage indicators.
        """

        # Making title ISO
        make_iso(
            self.source_dir + u'/bases/title/title',
            self.source_dir + u'/bases/title/title.iso',
            self.cisis_dir
        )
        self.client.put(
            self.source_dir + u'/bases/title/title.iso',
            self.destiny_dir + u'/title.iso'
        )

        # Making issue ISO
        make_iso(
            self.source_dir + u'/bases/issue/issue',
            self.source_dir + u'/bases/issue/issue.iso',
            self.cisis_dir
        )
        self.client.put(
            self.source_dir + u'/bases/issue/issue.iso',
            self.destiny_dir + u'/issue.iso'
        )

        # Making issues ISO
        make_iso(
            self.source_dir + u'/bases/artigo/artigo',
            self.source_dir + u'/bases/issue/issues.iso',
            self.cisis_dir,
            u'TP=I'
        )
        self.client.put(
            self.source_dir + u'/bases/issue/issues.iso',
            self.destiny_dir + u'/issues.iso'
        )

        # Making article ISO
        make_iso(
            self.source_dir + u'/bases/artigo/artigo',
            self.source_dir + u'/bases/artigo/artigo.iso',
            self.cisis_dir,
            u'TP=H',
            u'''"proc='d91<91 0>',ref(mfn-1,v91),'</91>'"'''
        )
        self.client.put(
            self.source_dir + u'/bases/artigo/artigo.iso',
            self.destiny_dir + u'/artigo.iso'
        )

        # Making bib4cit ISO
        make_iso(
            self.source_dir + u'/bases/artigo/artigo',
            self.source_dir + u'/bases/artigo/bib4cit.iso',
            self.cisis_dir,
            u'TP=C'
        )
        self.client.put(
            self.source_dir + u'/bases/artigo/bib4cit.iso',
            self.destiny_dir + u'/bib4cit.iso'
        )

    def send_static_reports(self):
        """
        This method will prepare and send static reports to the SciELO FPT.
        The static reports are:
            static_pdf_files.txt
                List of PDF files available in the server side file system.
            static_html_files.txt
                List of HTML files available in the server side file system.
            static_xml_files.txt
                List of XML files available in the server side file system.
            static_section_catalog.txt
                List of the journals sections extracted from the issue database.
        Those files are used to improve the metadata quality and completeness of
        the Article Meta API.
        """

        make_static_file_report(self.source_dir, u'pdf')
        self.client.put(
            self.source_dir + u'/bases/reports/static_pdf_files.txt',
            self.destiny_dir + u'/static_pdf_files.txt'
        )
        make_static_file_report(self.source_dir, u'translation')
        self.client.put(
            self.source_dir + u'/bases/reports/static_html_files.txt',
            self.destiny_dir + u'/static_html_files.txt'
        )
        make_static_file_report(self.source_dir, u'xml')
        self.client.put(
            self.source_dir + u'/bases/reports/static_xml_files.txt',
            self.destiny_dir + u'/static_xml_files.txt'
        )
        make_section_catalog_report(self.source_dir, self.cisis_dir)
        self.client.put(
            self.source_dir + u'/bases/reports/static_section_catalog.txt',
            self.destiny_dir + u'/static_section_catalog.txt'
        )

    def run(self, source_type=None):

        source_type = source_type if source_type else self.source_type

        if source_type == u'isos':
            self.send_isos()
        elif source_type == u'reports':
            self.send_static_reports()
        else:
            self.send_isos()
            self.send_static_reports()


def main():

    setts = settings.get(u'app:main', {})

    parser = argparse.ArgumentParser(
        description=u'Tools to send ISO databases to SciELO Network processing'
    )

    parser.add_argument(
        u'--source_type',
        u'-t',
        choices=['isos', 'reports'],
        help=u'Type of data that will be send to the server'
    )

    parser.add_argument(
        u'--cisis_dir',
        u'-r',
        default=setts.get(u'cisis_dir', u''),
        help=u'absolute path to the source where the ISIS utilitaries are where installed. It is not necessary to informe when the utiliaries are in the syspath.'
    )

    parser.add_argument(
        u'--source_dir',
        u'-s',
        default=setts.get(u'source_dir', u'.'),
        help=u'absolute path where the SciELO site was installed. this directory must contain the directories bases, htcos, proc and serial'
    )

    parser.add_argument(
        u'--destiny_dir',
        u'-d',
        default=setts.get(u'destiny_dir', u'.'),
        help=u'absolute path (server site) where the SciELO site was installed. this directory must contain the directories bases, htcos, proc and serial'
    )

    parser.add_argument(
        u'--server',
        u'-f',
        default=setts.get(u'server', u'localhost'),
        help=u'FTP or SFTP Server'
    )

    parser.add_argument(
        u'--port',
        u'-x',
        default=setts.get(u'port', u'22'),
        choices=['22','21'],
        help=u'22 for SFTP connection or 21 for FTP connection'
    )

    parser.add_argument(
        u'--user',
        u'-u',
        default=setts.get(u'user', u'anonymous'),
        help=u'FTP or SFTP username'
    )

    parser.add_argument(
        u'--password',
        u'-p',
        default=setts.get(u'password', u'anonymous'),
        help=u'FTP or SFTP password'
    )

    parser.add_argument(
        u'--logging_level',
        u'-l',
        default=u'DEBUG',
        choices=[u'DEBUG', u'INFO', u'WARNING', u'ERROR', u'CRITICAL'],
        help=u'Log level'
    )

    args = parser.parse_args()
    _config_logging(args.logging_level)

    delivery = Delivery(
        args.source_type,
        args.cisis_dir,
        args.source_dir,
        args.destiny_dir,
        args.server,
        args.port,
        args.user,
        args.password
    )

    delivery.run()
