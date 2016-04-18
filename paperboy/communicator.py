# coding: utf-8
import logging
import paramiko
from paramiko.client import SSHClient
from paramiko import ssh_exception
from ftplib import FTP as FTPLIB
import ftplib

logger = logging.getLogger(__name__)

class Communicator(object):

    def __init__(self, host, port, user, password):
        
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self._active_client = None

class FTP(Communicator):
    ftp_client = None

    @property
    def client(self):
        self.ftp_client = FTPLIB(self.host)
        try:
            self.ftp_client.login(user=self.user, passwd=self.password)
        except ftplib.error_perm:
            logger.error(u'Fail while connecting through FTP. Check your creadentials.')
        else:
            return self.ftp_client

    def exists_dir(self, path):
        logger.info(u'Checking if directory already exists (%s)' % path)

        try:
            stdout = self.client.dir(str(path))
            logger.debug(u'Directory already exists (%s)' % path)
            return True
        except:
            logger.debug(u'Directory do not exists (%s)' % path)

        return False

    def mkdir(self, path):

        logger.info(u'Creating directory (%s)' % path)

        try:
            self.client.mkd(path)
            logger.debug(u'Directory has being created (%s)' % path)
        except ftplib.error_perm as e:
            if self.exists_dir(path):
                logger.warning(u'Directory already exists (%s): %s', path, e.message)
            else:
                logger.error(u'Fail while creating directory (%s): %s', path, e.message)
    
    def chdir(self, path):

        logger.info(u'Changing to directory (%s)' % path)

        try:
            self.client.chdir(path)
        except IOError as e:
            logger.error(u'Fail while accessing directory (%s): %s' % (
                path, e.strerror)
            )
            raise(e)

    def put(self, from_fl, to_fl):

        logger.info(u'Copying file from (%s) to (%s)' % (
            from_fl,
            to_fl
        ))

        self.client.storbinary('STOR %s' % to_fl , open(from_fl, 'r'))
        logger.debug(u'File has being copied (%s)' % to_fl)

class SFTP(Communicator):
    ssh_client = None

    @property
    def client(self):

        if self.ssh_client and self.ssh_client.get_transport().is_active():
            return self._active_client

        self._active_client = self._client()

        return self._active_client

    def _client(self):

        logger.info(u'Conecting through SSH to the server (%s:%s)',self.host, self.port)

        try:
            self.ssh_client = SSHClient()
            self.ssh_client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()
            )
            self.ssh_client.connect(
                self.host,
                username=self.user,
                password=self.password,
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

    def mkdir(self, path):

        logger.info(u'Creating directory (%s)' % path)

        try:
            self.client.mkdir(path)
            logger.debug(u'Directory has being created (%s)' % path)
        except IOError:
            try:
                self.client.listdir(path)
                logger.warning(u'Directory already exists (%s)' % path)
            except IOError as e:
                logger.error(u'Fail while creating directory (%s): %s' % (
                    path, e.strerror)
                )
                raise(e)

    def chdir(self, path):

        logger.info(u'Changing to directory (%s)' % path)

        try:
            self.client.chdir(path)
        except IOError as e:
            logger.error(u'Fail while accessing directory (%s): %s' % (
                path, e.strerror)
            )
            raise(e)

    def put(self, from_fl, to_fl):

        logger.info(u'Copying file from (%s) to (%s)' % (
            from_fl,
            to_fl
        ))

        try:
            self.client.put(from_fl, to_fl)
            logger.debug(u'File has being copied (%s)' % to_fl)
        except IOError as e:
            logger.error(u'Fail while copying file (%s): %s' % (
                to_fl, e.strerror)
            )