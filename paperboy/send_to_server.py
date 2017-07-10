# coding: utf-8
import argparse
import logging
import logging.config
import os
import subprocess

from paperboy.utils import settings
from paperboy.communicator import SFTP, FTP

logger = logging.getLogger(__name__)

ALLOWED_ITENS = ['serial', 'pdfs', 'images', 'translations']

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


def master_conversor(mst_input, mst_output, cisis_dir=None):

    logger.debug(u'Running database conversion for %s', mst_input)

    status = '1'  # erro de acordo com stdout do CISIS

    command = remove_last_slash(cisis_dir) + '/crunchmf' if cisis_dir else 'crunchmf'
    logger.debug(u'Running: %s %s %s', command, mst_input, mst_output)
    try:
        status = subprocess.call([command, mst_input, mst_output])
    except OSError:
        logger.error(u'Error while running crunchmf, check if the command is available on the syspath, or the CISIS path was correctly indicated in the config file')

    if str(status) == '0':
        logger.debug(u'Conversion done for %s', mst_input)
        return True

    if str(status) == '1':
        logger.error(u'Conversion did not work fot %s', mst_input)
        return False

    return False


def parse_scilista(scilista):

    logger.info(u'Loading scilista (%s)', scilista)

    lista = []

    try:
        f = open(scilista, 'r')
    except IOError:
        logger.error(
            u'Fail while loading scilista, file not found (%s)',
            scilista
        )
    else:
        with f:
            count = 0
            for line in f:
                line = line.strip()
                count += 1
                splited_line = [i.strip().lower() for i in line.split(' ')]

                if len(splited_line) > 3 or len(splited_line) < 2:
                    logger.warning(
                        u'Wrong value in the file (%s) line (%d): %s',
                        scilista,
                        count,
                        line
                    )
                    continue

                if len(splited_line) == 3:  # issue to remove
                    if splited_line[2].lower() == 'del':
                        lista.append((splited_line[0], splited_line[1], True))
                    else:
                        lista.append((splited_line[0], splited_line[1], False))

                if len(splited_line) == 2:  # issue to remove
                    lista.append((splited_line[0], splited_line[1], False))

        logger.info(u'scilista loaded (%s)', scilista)

    return lista


def remove_last_slash(path):
    path = path.replace('\\', '/')

    try:
        return path[:-1] if path[-1] == '/' else path
    except IndexError:
        return path


class Delivery(object):

    def __init__(self, source_type, cisis_dir, scilista, source_dir, destiny_dir,
            compatibility_mode, server, server_type, port, user, password):

        self._scilista = parse_scilista(scilista)
        self.scilista = scilista
        self.cisis_dir = remove_last_slash(cisis_dir)
        self.source_type = source_type
        self.source_dir = remove_last_slash(source_dir)
        self.destiny_dir = remove_last_slash(destiny_dir)
        self.compatibility_mode = compatibility_mode

        if str(server_type) == 'sftp':
            self.client = SFTP(server, int(port), user, password)
        elif str(server_type) == 'ftp':
            self.client = FTP(server, int(port), user, password)
        else:
            raise TypeError(u'server_type must be ftp or sftp')

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

    def transfer_data_general(self, base_path):

        base_path = base_path.replace(u'\\', u'/')

        # Cria a estrutura de diretorio informada em base_path dentro de destiny_dir
        path = u''
        for item in base_path.split(u'/'):
            path += u'/' + item
            self.client.mkdir(self.destiny_dir + path)

        # Cria recursivamente todo conteudo baixo o source_dir + base_path
        tree = os.walk(self.source_dir + u'/' + base_path)
        for item in tree:
            root = item[0].replace(u'\\', u'/')
            current = root.replace(self.source_dir+u'/', '')
            dirs = item[1]
            files = item[2]

            for fl in files:
                from_fl = root + u'/' + fl
                to_fl = self.destiny_dir + u'/' + current + u'/' + fl
                self.client.put(from_fl, to_fl)

            for directory in dirs:
                self.client.mkdir(self.destiny_dir + u'/' + current + u'/' + directory)

    def transfer_data_databases(self, base_path):
        """
        base_path: directory inside the source path that will be transfered.
        ex: serial/rsap img/revistas/rsap
        compatibility_mode: Will convert the original MST and XRF files for the
        inversed SO system of the source data.
        ex: if the source data is on a windows machine, it will be converted to
        linux compatible files. If the source data is on a linux machine it will
        convert the files to windown compatible files. The default is false.
        """

        base_path = base_path.replace(u'\\', u'/')

        allowed_extensions = [u'mst', u'xrf']

        # Cria a estrutura de diretorio informada em base_path dentro de destiny_dir
        path = u''
        for item in base_path.split(u'/'):
            path += u'/' + item
            self.client.mkdir(self.destiny_dir + path)

        # Cria recursivamente todo conteudo baixo o source_dir + base_path
        tree = os.walk(self.source_dir + u'/' + base_path)
        converted = set()
        for item in tree:
            root = item[0].replace(u'\\', u'/')
            current = root.replace(self.source_dir + u'/', u'')
            dirs = item[1]
            files = item[2]

            for fl in files:
                if not fl[-3:].lower() in allowed_extensions:
                    continue
                from_fl = root + u'/' + fl
                from_fl_name = from_fl[:-4]
                converted_fl = from_fl_name + u'_converted'
                to_fl = self.destiny_dir + u'/' + current + u'/' + fl

                if not self.compatibility_mode:
                    self.client.put(from_fl, to_fl)
                    continue

                if from_fl_name in converted:
                    continue

                converted.add(from_fl_name)
                convertion_status = master_conversor(
                    from_fl_name,
                    converted_fl,
                    cisis_dir=self.cisis_dir
                )

                if not convertion_status:
                    continue

                if convertion_status:
                    from_fl = converted_fl

                to_fl = to_fl[:-4]
                for extension in allowed_extensions:
                    self.client.put(from_fl + u'.' + extension, to_fl + u'.' + extension)
                    self._local_remove(from_fl + u'.' + extension)

            for directory in dirs:
                self.client.mkdir(self.destiny_dir + u'/' + current + u'/' + directory)

    def run_serial(self):

        self.client.mkdir(self.destiny_dir + u'/serial')

        logger.info(u'Copying scilista.lst file')
        self.client.put(self.scilista, self.destiny_dir + u'/serial/scilista.lst')

        logger.info(u'Copying issue database')
        self.transfer_data_databases(u'serial/issue')

        logger.info(u'Copying title database')
        self.transfer_data_databases(u'serial/title')

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]

            # pulando itens do scilista indicados para exclusao, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(
                u'Copying databases from %s %s',
                journal_acronym,
                issue_label
            )

            self.transfer_data_databases(u'serial/%s/%s/base' % (
                journal_acronym, issue_label)
            )

    def run_pdfs(self):

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]

            # pulando itens do scilista indicados para exclusao, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(
                u'Copying pdf\'s from %s %s',
                journal_acronym,
                issue_label
            )

            self.transfer_data_general(u'bases/pdf/%s/%s' % (
                journal_acronym, issue_label)
            )

    def run_translations(self):

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]

            # pulando itens do scilista indicados para exclusao, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(
                u'Copying translations from %s %s',
                journal_acronym,
                issue_label
            )

            self.transfer_data_general(u'bases/translation/%s/%s' % (
                journal_acronym, issue_label)
            )

    def run_xmls(self):

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]

            # pulando itens do scilista indicados para exclusao, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(
                u'Copying xmls from %s %s',
                journal_acronym,
                issue_label
            )

            self.transfer_data_general(u'bases/xml/%s/%s' % (
                journal_acronym, issue_label)
            )

    def run_images(self):

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]

            # pulando itens do scilista indicados para exclusao, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(
                u'Copying images from %s %s',
                journal_acronym,
                issue_label
            )

            self.transfer_data_general(u'htdocs/img/revistas/%s/%s' % (
                journal_acronym, issue_label)
            )

    def run(self, source_type=None):

        source_type = source_type if source_type else self.source_type

        if source_type == u'pdfs':
            self.run_pdfs()
        elif source_type == u'images':
            self.run_images()
        elif source_type == u'translations':
            self.run_translations()
        elif source_type == u'databases':
            self.run_serial()
        elif source_type == u'xmls':
            self.run_xmls()
        else:
            self.run_serial()
            self.run_images()
            self.run_pdfs()
            self.run_translations()
            self.run_xmls()


def main():

    setts = settings.get('app:main', {})

    parser = argparse.ArgumentParser(
        description=u'Tools to send images, PDF\'s, translations and databases from the local SciELO sites to the stage and production servers'
    )

    parser.add_argument(
        u'--source_type',
        u'-t',
        choices=[u'pdfs', u'images', u'translations', u'xmls', u'databases'],
        help=u'Type of data that will be send to the server'
    )

    parser.add_argument(
        u'--cisis_dir',
        u'-r',
        default=setts.get(u'cisis_dir', u''),
        help=u'absolute path to the source where the ISIS utilitaries are where installed. It is not necessary to informe when the utiliaries are in the syspath.'
    )

    parser.add_argument(
        u'--scilista',
        u'-i',
        default=setts.get(u'scilista', u'./serial/scilista.lst'),
        help=u'absolute path to the scilista.lst file'
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
        u'--compatibility_mode',
        u'-m',
        action=u'store_true',
        help=u'Activate the compatibility mode between operating systems. It is necessary to have the CISIS configured in the syspath or in the configuration file'
        )

    parser.add_argument(
        u'--server',
        u'-f',
        default=setts.get(u'server', u'localhost'),
        help=u'FTP or SFTP'
    )

    parser.add_argument(
        u'--server_type',
        u'-e',
        default=setts.get(u'server_type', u'sftp'),
        choices=['ftp', 'sftp']
    )

    parser.add_argument(
        u'--port',
        u'-x',
        default=setts.get(u'port', u'22'),
        help=u'usually 22 for SFTP connection or 21 for FTP connection'
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
        args.scilista,
        args.source_dir,
        args.destiny_dir,
        args.compatibility_mode,
        args.server,
        args.server_type,
        args.port,
        args.user,
        args.password
    )

    delivery.run()
