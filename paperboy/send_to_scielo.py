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


def make_iso(mst_input, iso_output, cisis_dir=None):

    logger.debug(u'Making iso for %s' % mst_input)

    status = '1'  # erro de acordo com stdout do CISIS

    command = remove_last_slash(cisis_dir) + '/mx' if cisis_dir else 'mx'
    command = [command, mst_input, 'iso=%s' % (iso_output), '-all now']

    logger.debug('Running: %s' % command)
    try:
        status = subprocess.call(command)
    except OSError as e:
        logger.error(u'Error while running mx, check if the command is available on the syspath, or the CISIS path was correctly indicated in the config file')

    if str(status) == '0':
        logger.debug(u'ISO creation done for %s' % mst_input)
        return True

    if str(status) == '1':
        logger.error(u'ISO creation did not work fot %s' % mst_input)
        return False

    return False


def remove_last_slash(path):
    path = path.replace('\\', '/')

    try:
        return path[:-1] if path[-1] == '/' else path
    except IndexError:
        return path


class Delivery(object):

    def __init__(self, cisis_dir, source_dir, destiny_dir, ssh_server, ssh_port,
            ssh_user, ssh_password):

        self.cisis_dir = remove_last_slash(cisis_dir)
        self.source_dir = remove_last_slash(source_dir)
        self.destiny_dir = remove_last_slash(destiny_dir)
        self.ssh_server = ssh_server
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.sftp_client = self._sftp_client()

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
                password=self.ssh_password
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

    def run(self, source_type=None):

        self.make_iso(
            self.source_dir + '/bases/title/title',
            '/bases/title/title.iso',
            self.cisis_dir
        )


def main():

    setts = settings.get('app:main', {})

    parser = argparse.ArgumentParser(
        description='Tools to send ISO databases to SciELO Network processing'
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
        args.cisis_dir,
        args.source_dir,
        args.destiny_dir,
        args.ssh_server,
        args.ssh_port,
        args.ssh_user,
        args.ssh_password
    )

    delivery.run()
