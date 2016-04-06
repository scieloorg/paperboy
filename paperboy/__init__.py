#coding: utf-8
import argparse
import logging
import os
import subprocess
from paperboy.utils import settings
import paramiko
from paramiko.client import SSHClient
from paramiko import ssh_exception

logger = logging.getLogger(__name__)

ALLOWED_ITENS = ['serial', 'pdfs', 'images', 'translations']


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


def master_conversor(mst_input, mst_output, cisis_dir=None):

    logger.debug(u'Realizando conversão de bases para %s' % mst_input)

    status = '1'  # erro de acordo com stdout do CISIS

    command = remove_last_slash(cisis_dir) + '/crunchmf' if cisis_dir else 'crunchmf'
    logger.debug('Executando: %s' % command)
    try:
        status = subprocess.call([command, mst_input, mst_output])
    except OSError as e:
        logger.error(u'Erro ao executar crunchmf, verifique se o comando esta no syspath, ou se o path do cisis foi indicado corretamente no arquivo de configuração')

    if str(status) == '0':
        logger.debug(u'Conversão realizada para %s' % mst_input)
        return True

    if str(status) == '1':
        logger.error(u'Conversão não funcionou para %s' % mst_input)
        return False

    return False


def parse_scilista(scilista):

    logger.info(u'Carregando scilista (%s)' % scilista)

    lista = []

    try:
        f = open(scilista, 'r')
    except IOError:
        logger.error('Falha ao carregar scilista, arquivo não encontrado (%s)' % scilista)
    else:
        with f:
            count = 0
            for line in f:
                line = line.strip()
                count += 1
                splited_line = [i.strip().lower() for i in line.split(' ')]

                if len(splited_line) > 3 or len(splited_line) < 2:
                    logger.warning(u'Valor errado no arquivo (%s) linha (%d): %s' % (
                        scilista, count, line))
                    continue

                if len(splited_line) == 3:  # issue to remove
                    if splited_line[2].lower() == 'del':
                        lista.append((splited_line[0], splited_line[1], True))
                    else:
                        lista.append((splited_line[0], splited_line[1], False))

                if len(splited_line) == 2:  # issue to remove
                    lista.append((splited_line[0], splited_line[1], False))

        logger.info(u'scilista carregada (%s)' % scilista)

    return lista


def remove_last_slash(path):
    path = path.replace('\\', '/')

    try:
        return path[:-1] if path[-1] == '/' else path
    except IndexError:
        return path


class Delivery(object):

    def __init__(self, source_type, cisis_dir, scilista, source_dir, destiny_dir,
            compatibility_mode, ssh_server, ssh_port, ssh_user, ssh_password):

        self._scilista = parse_scilista(scilista)
        self.cisis_dir = remove_last_slash(cisis_dir)
        self.source_type = source_type
        self.source_dir = remove_last_slash(source_dir)
        self.destiny_dir = remove_last_slash(destiny_dir)
        self.compatibility_mode = compatibility_mode
        self.ssh_server = ssh_server
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.sftp_client = self._sftp_client()

    def _sftp_client(self):

        logger.info(u'Conectando via SSH ao servidor (%s:%s)' % (
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
            logger.error(u'Falha ao conectar ao SSH. Verificar credenciais.')
            return None
        except ssh_exception.NoValidConnectionsError:
            logger.error(u'Falha ao conectar ao SSH. Verificar credenciais ou disponibilidade do servidor.')
            return None
        else:
            return self.ssh_client.open_sftp()

    def _mkdir(self, path):

        logger.info(u'Criando diretório (%s)' % path)

        try:
            self.sftp_client.mkdir(path)
            logger.debug(u'Diretório criado (%s)' % path)
        except IOError:
            try:
                self.sftp_client.listdir(path)
                logger.warning(u'Diretório já existe (%s)' % path)
            except IOError as e:
                logger.error(u'Falha ao criar diretório (%s): %s' % (
                    path, e.strerror)
                )
                raise(e)

    def _chdir(self, path):

        logger.info(u'Mudando para diretório (%s)' % path)

        try:
            self.sftp_client.chdir(path)
        except IOError as e:
            logger.error(u'Falha ao acessar diretório (%s): %s' % (
                path, e.strerror)
            )
            raise(e)

    def _put(self, from_fl, to_fl):

        logger.info(u'Copiando arquivo de (%s) para (%s)' % (
            from_fl,
            to_fl
        ))

        try:
            self.sftp_client.put(from_fl, to_fl)
            logger.debug(u'Arquivo copiado (%s)' % to_fl)
        except IOError as e:
            logger.error(u'Falha ao copiar arquivo (%s): %s' % (
                to_fl, e.strerror)
            )

    def _local_remove(self, path):

        logger.info(u'Removendo arquivo temporário (%s)' % path)

        try:
            os.remove(path)
            logger.debug(u'Arquivo temporário removido (%s)' % path)
        except OSError as e:
            logger.error(u'Falha ao remover arquivo temporário (%s): %s' % (
                path, e.strerror)
            )

    def transfer_data_general(self, base_path):

        base_path = base_path.replace('\\', '/')

        # Cria a estrutura de diretório informada em base_path dentro de destiny_dir
        path = ''
        for item in base_path.split('/'):
            path += '/' + item
            self._mkdir(self.destiny_dir + path)

        # Cria recursivamente todo conteúdo baixo o source_dir + base_path
        tree = os.walk(self.source_dir + '/' + base_path)
        for item in tree:
            current = item[0].replace(self.source_dir+'/', '')
            dirs = item[1]
            files = item[2]

            for fl in files:
                from_fl = item[0] + '/' + fl
                to_fl = self.destiny_dir + '/' + current + '/' + fl
                self._put(from_fl, to_fl)

            for directory in dirs:
                self._mkdir(self.destiny_dir + '/' + current + '/' + directory)

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

        base_path = base_path.replace('\\', '/')

        allowed_extensions = ['mst', 'xrf']

        # Cria a estrutura de diretório informada em base_path dentro de destiny_dir
        path = ''
        for item in base_path.split('/'):
            path += '/' + item
            self._mkdir(self.destiny_dir + path)

        # Cria recursivamente todo conteúdo baixo o source_dir + base_path
        tree = os.walk(self.source_dir + '/' + base_path)
        converted = set()
        for item in tree:
            current = item[0].replace(self.source_dir+'/', '')
            dirs = item[1]
            files = item[2]

            for fl in files:
                if not fl[-3:].lower() in allowed_extensions:
                    continue
                from_fl = item[0] + '/' + fl
                from_fl_name = from_fl[:-4]
                converted_fl = from_fl_name + '_converted'
                to_fl = self.destiny_dir + '/' + current + '/' + fl

                if not self.compatibility_mode:
                    self._put(from_fl, to_fl)
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
                    self._put(from_fl + '.' + extension, to_fl + '.' + extension)
                    self._local_remove(from_fl + '.' + extension)

            for directory in dirs:
                self._mkdir(self.destiny_dir + '/' + current + '/' + directory)

    def run_serial(self):

        if not self.sftp_client:
            return None

        logger.info('Copiando base issue')
        self.transfer_data_databases('serial/issue')

        logger.info('Copiando base title')
        self.transfer_data_databases('serial/title')

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]
            to_remove = item[2]

            # pulando itens do scilista indicados para exclusão, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(u'Copiando bases de %s %s' % (journal_acronym, issue_label))
            self.transfer_data_databases('serial/%s/%s/base' % (
                journal_acronym, issue_label)
            )

    def run_pdfs(self):

        if not self.sftp_client:
            return None

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]
            to_remove = item[2]

            # pulando itens do scilista indicados para exclusão, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(u'Copiando pdfs de %s %s' % (journal_acronym, issue_label))
            self.transfer_data_general('bases/pdf/%s/%s' % (
                journal_acronym, issue_label)
            )

    def run_translations(self):

        if not self.sftp_client:
            return None

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]
            to_remove = item[2]

            # pulando itens do scilista indicados para exclusão, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(u'Copiando traduções de %s %s' % (journal_acronym, issue_label))
            self.transfer_data_general('bases/translation/%s/%s' % (
                journal_acronym, issue_label)
            )

    def run_xmls(self):

        if not self.sftp_client:
            return None

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]
            to_remove = item[2]

            # pulando itens do scilista indicados para exclusão, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(u'Copiando xmls de %s %s' % (journal_acronym, issue_label))
            self.transfer_data_general('bases/xml/%s/%s' % (
                journal_acronym, issue_label)
            )

    def run_images(self):

        if not self.sftp_client:
            return None

        for item in self._scilista:
            journal_acronym = item[0]
            issue_label = item[1]
            to_remove = item[2]

            # pulando itens do scilista indicados para exclusão, ex: rsap v12n3 del
            if item[2]:
                continue

            logger.info(u'Copiando imagens de %s %s' % (
                journal_acronym, issue_label)
            )

            self.transfer_data_general('htdocs/img/revistas/%s/%s' % (
                journal_acronym, issue_label)
            )

    def run(self, source_type=None):

        source_type = source_type if source_type else self.source_type

        if source_type == 'pdfs':
            self.run_pdfs()
        elif source_type == 'images':
            self.run_images()
        elif source_type == 'translations':
            self.run_translations()
        elif source_type == 'databases':
            self.run_serial()
        elif source_type == 'xmls':
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
        description=u'Utilitário para envio de Imagens, PDF\'s, Traducões e Bases de sites locais SciELO para os servidores de homologação e produção'
    )

    parser.add_argument(
        '--source_type',
        '-t',
        choices=['pdfs', 'images', 'translations', 'xmls', 'databases'],
        help=u'tipo de dados que será enviado para o servidor'
    )

    parser.add_argument(
        '--cisis_dir',
        '-r',
        default=setts.get('cisis_dir', ''),
        help=u'path absoluto para o local onde estão instalados os utilitários ISIS. Caso o utilitário esteja no syspath, não será necessário informar esse dado.'
    )

    parser.add_argument(
        '--scilista',
        '-i',
        default=setts.get('scilista', './serial/scilista.lst'),
        help=u'caminho absoluto para o arquivo scilista.lst'
    )

    parser.add_argument(
        '--source_dir',
        '-s',
        default=setts.get('source_dir', '.'),
        help=u'caminho absoluto onde esta instalado o site scielo, contendo os diretórios, bases, htdocs, proc e serial.'
    )

    parser.add_argument(
        '--destiny_dir',
        '-d',
        default=setts.get('destiny_dir', '.'),
        help=u'caminho absoluto onde esta instalado o site scielo, contendo os diretórios, bases, htdocs, proc e serial.'
    )

    parser.add_argument(
        '--compatibility_mode',
        '-m',
        action='store_true',
        help=u'Ativar modo de compatibilidade entre sistemas operacionais. É necessário ter o CISIS de origem dos dados configurado no syspath ou no arquivo de configuração'
        )

    parser.add_argument(
        '--ssh_server',
        '-f',
        default=setts.get('ssh_server', 'localhost'),
        help=u'FTP'
    )

    parser.add_argument(
        '--ssh_port',
        '-x',
        default=setts.get('ssh_port', '22'),
        help=u'FTP port'
    )

    parser.add_argument(
        '--ssh_user',
        '-u',
        default=setts.get('ssh_user', 'anonymous'),
        help=u'Usuário do ftp'
    )

    parser.add_argument(
        '--ssh_password',
        '-p',
        default=setts.get('ssh_password', 'anonymous'),
        help=u'Senha do ftp'
    )

    parser.add_argument(
        '--logging_file',
        '-o',
        help=u'Caminho completo para o arquivo de logs'
    )

    parser.add_argument(
        '--logging_level',
        '-l',
        default='DEBUG',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help=u'Nível de log'
    )

    args = parser.parse_args()
    _config_logging(args.logging_level, args.logging_file)

    delivery = Delivery(
        args.source_type,
        args.cisis_dir,
        args.scilista,
        args.source_dir,
        args.destiny_dir,
        args.compatibility_mode,
        args.ssh_server,
        args.ssh_port,
        args.ssh_user,
        args.ssh_password
    )

    delivery.run()
