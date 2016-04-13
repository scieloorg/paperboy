# coding: utf-8
import argparse
import logging
import os
import subprocess
from paperboy.utils import settings
import paramiko
from paramiko.client import SSHClient
from paramiko import ssh_exception

logger = logging.getLogger(__name__)


def _config_logging(logging_level='INFO', logging_file=None):

    allowed_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.setLevel(allowed_levels.get(logging_level, 'INFO'))

    if logging_file:
        hl = logging.FileHandler(logging_file, mode='a')
    else:
        hl = logging.StreamHandler()

    hl.setFormatter(formatter)
    hl.setLevel(allowed_levels.get(logging_level, 'INFO'))

    logger.addHandler(hl)

    return logger


def make_iso(mst_input, iso_output, cisis_dir=None, fltr=None, proc=None):

    logger.info(u'Making iso for %s' % mst_input)

    status = '1'  # erro de acordo com stdout do CISIS


    command = [remove_last_slash(cisis_dir) + '/mx' if cisis_dir else 'mx']
    command.append(mst_input)
    if fltr:
        command.append('btell=0')
        command.append(fltr)
    if proc:
        command.append(proc)
    command.append('iso=%s' % (iso_output))
    command.append('-all')
    command.append('now')

    logger.debug('Running: %s' % ' '.join(command))
    try:
        status = subprocess.call(command)
    except OSError as e:
        logger.error(u'Error while running mx, check if the command is available on the syspath, or the CISIS path was correctly indicated in the config file')

    if str(status) == '0':
        logger.debug(u'ISO %s creation done for %s' % (iso_output, mst_input))
        return True

    if str(status) == '1':
        logger.error(u'ISO creation did not work for %s' % mst_input)
        return False

    return False


def make_section_catalog_report(source_dir, cisis_dir):

    logger.info(u'Making report static_section_catalog.txt')

    command = """mkdir -p %s/bases/reports; %s/mx %s/bases/issue/issue btell=0 "pft=if p(v49) then (v35[1],v65[1]*0.4,s(f(val(s(v36[1]*4.3))+10000,2,0))*1.4,'|',v49^l,'|',v49^c,'|',v49^t,/) fi" lw=0 -all now > %s/bases/reports/static_section_catalog.txt""" % (
        source_dir,
        cisis_dir,
        source_dir,
        source_dir,
    )

    logger.debug('Running: %s' % command)

    try:
        status = subprocess.Popen(command, shell=True)
    except OSError as e:
        logger.error(u'Error while creating report, static_section_catalog.txt was not updated')

    logger.debug(u'Report static_section_catalog.txt done')

def make_static_file_report(source_dir, report):

    extension_name = 'htm' if report == 'translation' else report
    report_name =  'html' if report == 'translation' else report

    logger.info(u'Making report static_%s_files.txt' % report_name)

    command = 'mkdir -p %s/bases/%s; mkdir -p %s/bases/reports; cd %s/bases/%s; find . -name "*.%s*" > %s/bases/reports/static_%s_files.txt' %(
        source_dir,
        report,
        source_dir,
        source_dir,
        report,
        extension_name,
        source_dir,
        report_name
    )

    logger.debug('Running: %s' % command)

    try:
        status = subprocess.Popen(command, shell=True)
    except OSError as e:
        logger.error(u'Error while creating report, static_%s_files.txt was not updated' % report_name)

    logger.debug(u'Report static_%s_files.txt done' % report_name)

def remove_last_slash(path):
    path = path.replace('\\', '/')

    try:
        return path[:-1] if path[-1] == '/' else path
    except IndexError:
        return path


class Delivery(object):

    def __init__(self, source_type, cisis_dir, source_dir, destiny_dir, ssh_server,
                 ssh_port, ssh_user, ssh_password):

        self.source_type = source_type
        self.cisis_dir = remove_last_slash(cisis_dir)
        self.source_dir = remove_last_slash(source_dir)
        self.destiny_dir = remove_last_slash(destiny_dir)
        self.ssh_server = ssh_server
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.ssh_client = None
        self._active_sftp_client = None

    @property
    def sftp_client(self):

        if self.ssh_client and self.ssh_client.get_transport().is_active():
            return self._active_sftp_client

        self._active_sftp_client = self._sftp_client()

        return self._active_sftp_client

    def _sftp_client(self):

        logger.info(u'Conecting through SSH to the server (%s:%s)' % (
            self.ssh_server, self.ssh_port)
        )

        try:
            self.ssh_client = SSHClient()
            self.ssh_client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()
            )
            self.ssh_client.connect(
                self.ssh_server,
                username=self.ssh_user,
                password=self.ssh_password,
                compress=True
            )
        except ssh_exception.AuthenticationException:
            logger.error(u'Fail while connecting through SSH. Check your creadentials.')
            return None
        except ssh_exception.NoValidConnectionsError:
            logger.error(u'Fail while connecting through SSH. Check your credentials or the server availability.')
            return None
        else:
            return self.ssh_client.open_sftp()

    def _mkdir(self, path):

        logger.info(u'Creating directory (%s)' % path)

        try:
            self.sftp_client.mkdir(path)
            logger.debug(u'Directory has being created (%s)' % path)
        except IOError:
            try:
                self.sftp_client.listdir(path)
                logger.warning(u'Directory already exists (%s)' % path)
            except IOError as e:
                logger.error(u'Fail while creating directory (%s): %s' % (
                    path, e.strerror)
                )
                raise(e)

    def _chdir(self, path):

        logger.info(u'Changing to directory (%s)' % path)

        try:
            self.sftp_client.chdir(path)
        except IOError as e:
            logger.error(u'Fail while accessing directory (%s): %s' % (
                path, e.strerror)
            )
            raise(e)

    def _put(self, from_fl, to_fl):

        logger.info(u'Copying file from (%s) to (%s)' % (
            from_fl,
            to_fl
        ))

        try:
            self.sftp_client.put(from_fl, to_fl)
            logger.debug(u'File has being copied (%s)' % to_fl)
        except IOError as e:
            logger.error(u'Fail while copying file (%s): %s' % (
                to_fl, e.strerror)
            )

    def _local_remove(self, path):

        logger.info(u'Removing temporary file (%s)' % path)

        try:
            os.remove(path)
            logger.debug(u'Temporary has being file removed (%s)' % path)
        except OSError as e:
            logger.error(u'Fail while removing temporary file (%s): %s' % (
                path, e.strerror)
            )

    def send_isos(self):
        """
        This method will prepare and send article, issue, issues and bib4cit
        iso files to SciELO.

        Those files are used to produce bibliometric and site usage indicators.
        """

        ## Making title ISO
        make_iso(
            self.source_dir + '/bases/title/title',
            self.source_dir + '/bases/title/title.iso',
            self.cisis_dir
        )
        self._put(
            self.source_dir + '/bases/title/title.iso',
            self.destiny_dir + '/title.iso'
        )

        ## Making issue ISO
        make_iso(
            self.source_dir + '/bases/issue/issue',
            self.source_dir + '/bases/issue/issue.iso',
            self.cisis_dir
        )
        self._put(
            self.source_dir + '/bases/issue/issue.iso',
            self.destiny_dir + '/issue.iso'
        )

        ## Making issues ISO
        make_iso(
            self.source_dir + '/bases/artigo/artigo',
            self.source_dir + '/bases/issue/issues.iso',
            self.cisis_dir,
            'TP=I'
        )
        self._put(
            self.source_dir + '/bases/issue/issues.iso',
            self.destiny_dir + '/issues.iso'
        )

        ## Making article ISO
        make_iso(
            self.source_dir + '/bases/artigo/artigo',
            self.source_dir + '/bases/artigo/artigo.iso',
            self.cisis_dir,
            'TP=H',
            '''"proc='d91<91 0>',ref(mfn-1,v91),'</91>'"'''
        )
        self._put(
            self.source_dir + '/bases/artigo/artigo.iso',
            self.destiny_dir + '/artigo.iso'
        )

        ## Making bib4cit ISO
        make_iso(
            self.source_dir + '/bases/artigo/artigo',
            self.source_dir + '/bases/artigo/bib4cit.iso',
            self.cisis_dir,
            'TP=C'
        )
        self._put(
            self.source_dir + '/bases/artigo/bib4cit.iso',
            self.destiny_dir + '/bib4cit.iso'
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
        Those files are used to improve the metadata quality and completeness of the
        Article Meta API.
        """

        make_static_file_report(self.source_dir, 'pdf')
        self._put(
            self.source_dir + '/bases/reports/static_pdf_files.txt',
            self.destiny_dir + '/static_pdf_files.txt'
        )
        make_static_file_report(self.source_dir, 'translation')
        self._put(
            self.source_dir + '/bases/reports/static_html_files.txt',
            self.destiny_dir + '/static_html_files.txt'
        )
        make_static_file_report(self.source_dir, 'xml')
        self._put(
            self.source_dir + '/bases/reports/static_xml_files.txt',
            self.destiny_dir + '/static_xml_files.txt'
        )
        make_section_catalog_report(self.source_dir, self.cisis_dir)
        self._put(
            self.source_dir + '/bases/reports/static_section_catalog.txt',
            self.destiny_dir + '/static_section_catalog.txt'
        )


    def run(self, source_type=None):

        source_type = source_type if source_type else self.source_type

        if source_type == 'isos':
            self.send_isos()
        elif source_type == 'reports':
            self.send_static_reports()
        else:
            self.send_isos()
            self.send_static_reports()

def main():

    setts = settings.get('app:main', {})

    parser = argparse.ArgumentParser(
        description='Tools to send ISO databases to SciELO Network processing'
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
        u'--ssh_server',
        u'-f',
        default=setts.get(u'ssh_server', u'localhost'),
        help=u'FTP'
    )

    parser.add_argument(
        u'--ssh_port',
        u'-x',
        default=setts.get(u'ssh_port', u'22'),
        help=u'FTP port'
    )

    parser.add_argument(
        u'--ssh_user',
        u'-u',
        default=setts.get(u'ssh_user', u'anonymous'),
        help=u'FTP username'
    )

    parser.add_argument(
        u'--ssh_password',
        u'-p',
        default=setts.get(u'ssh_password', u'anonymous'),
        help=u'FTP password'
    )

    parser.add_argument(
        u'--logging_file',
        u'-o',
        help=u'absolute path to the log file'
    )

    parser.add_argument(
        u'--logging_level',
        u'-l',
        default=u'DEBUG',
        choices=[u'DEBUG', u'INFO', u'WARNING', u'ERROR', u'CRITICAL'],
        help=u'Log level'
    )

    args = parser.parse_args()
    _config_logging(args.logging_level, args.logging_file)

    delivery = Delivery(
        args.source_type,
        args.cisis_dir,
        args.source_dir,
        args.destiny_dir,
        args.ssh_server,
        args.ssh_port,
        args.ssh_user,
        args.ssh_password
    )

    delivery.run()
